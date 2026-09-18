"""A figure maintained in two documents must be the same figure in both.

`docs/index.html` is held by two modules — `test_site_committed.py` byte-diffs it against a
rebuild and `test_site_claims.py` checks the words around its figures. Nothing held the prose
documents, and by the audit's measure they carry five times as many figure-bearing lines as the
page does (`portfolio-index` `0010` B-5d). Most of that gap is not closable by a test: a figure in
`findings.md` is sourced to a run that is committed, and checking it would mean re-deriving the
run. **But one part of it is mechanical and is the part that has actually gone wrong across this
portfolio**: the same claim written into two documents, corrected in one of them, and left stale
in the other. B-5d measured 44 such lines here, two of them standing in three documents.

So this module does not try to source a figure to an artifact. It asserts the one thing that can
be asserted for free: **where two documents say almost the same thing, they must say the same
numbers.**

**The unit is a paragraph and not a line, and that is load-bearing.** The first version compared
physical lines and reported a disagreement between `findings.md` and `ADR-0002` over `0.30` —
which was a false positive: both documents carry the same three figures and wrap them at different
columns, so one physical line held `0.30` and the other held `0.30`, `0.32` and `72`. Comparing a
hard-wrapped document line by line measures the wrapping. Table rows stay their own units, because
a table row is one claim and is not wrapped.

*What this does not do.* It does not notice a figure that is wrong in **both** copies, a figure
that appears in only one document, or a claim rewritten far enough that the similarity bound stops
matching it. The bound is deliberately generous in one direction: a pair that drifts apart in
wording *and* in figures stops being compared, so this guard is at its strongest against exactly
the edit that motivates it — someone changing a number and nothing else.
"""

from __future__ import annotations

import difflib
import functools
import itertools
import re

from conftest import REPO_ROOT

#: The prose documents. `docs/index.html` is excluded because two modules already hold it, and
#: because it is generated: a figure in it cannot drift from its source without the byte-diff
#: saying so.
DOCUMENTS = (
    "README.md",
    "CLAUDE.md",
    "docs/findings.md",
    "docs/adr/0001_trust_boundary.md",
    "docs/adr/0002_placement.md",
)

#: Long enough to be a claim rather than a heading or a list marker, by the same measure `0010`
#: B-5d used to count them.
MIN_LENGTH = 30

#: How alike two passages must be before disagreeing figures are a defect rather than two
#: different sentences. High on purpose — see the module docstring's last paragraph.
SIMILARITY = 0.90


def conflict(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    """Whether two passages' figures actually contradict, rather than one saying more.

    **Each side must carry a figure the other does not.** Requiring the tuples to be equal was
    the first rule and it was wrong: `findings.md` says *"all 24 committed runs"* where
    `ADR-0002` says *"every committed run"*, which is one document naming a count and the other
    declining to — an omission, not a disagreement, and there are more of those in a record that
    summarises itself than there are real drifts. A changed value shows up as an extra figure on
    *both* sides, because one has the old number and the other has the new one.
    """
    return bool(set(left) - set(right)) and bool(set(right) - set(left))


#: The three characters this project groups digits with: a narrow no-break space, a no-break
#: space, and a plain one. Built with `chr` rather than typed, because a literal U+202F in source
#: is invisible to a reader, is ambiguous to `ruff`, and does not survive a shell heredoc — which
#: is the trap this line was written into on the first attempt.
GROUPING = chr(0x202F) + chr(0x00A0) + " "

#: A number, with those separators folded out, so a grouped figure reads as one number rather
#: than as two. The plain space has to be in the class because this project's prose uses it as a
#: group separator too — and that is also why the unit above is a passage: inside a table it
#: would weld adjacent cells.
_FIGURE = re.compile(rf"\d[\d{GROUPING}]*(?:[.,]\d+)?")
_SEPARATORS = re.compile(rf"[{GROUPING}]")


def figures(passage: str) -> tuple[str, ...]:
    """Every number in a passage, in order, with group separators removed."""
    return tuple(_SEPARATORS.sub("", m.group()) for m in _FIGURE.finditer(passage))


def passages(name: str) -> dict[str, int]:
    """Figure-bearing passages of one document -> the line each starts at.

    A table row is its own passage. Everything else is unwrapped to a paragraph first, because a
    hard-wrapped document compared line by line reports its own line breaks as disagreements.
    """
    text = (REPO_ROOT / name).read_text(encoding="utf-8")
    found: dict[str, int] = {}
    buffer: list[str] = []
    start = 0

    def flush() -> None:
        if buffer:
            joined = " ".join(buffer).strip()
            if len(joined) > MIN_LENGTH and any(c.isdigit() for c in joined):
                found.setdefault(joined, start)
            buffer.clear()

    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith("|"):
            flush()
            if len(line) > MIN_LENGTH and any(c.isdigit() for c in line):
                found.setdefault(line, number)
            continue
        if not buffer:
            start = number
        buffer.append(line)
    flush()
    return found


@functools.lru_cache(maxsize=1)
def _compared() -> tuple[int, tuple[str, ...]]:
    """(pairs compared, divergences). Computed once: the walk is quadratic and both tests want it.

    **The short-circuits are what make it affordable**, not an optimisation added afterwards.
    The naive walk ran 85 seconds against a suite that takes fifty, which is a guard nobody would
    leave switched on. `real_quick_ratio` and `quick_ratio` are `difflib`'s own upper bounds — if
    the cheap bound is already below the threshold the expensive match cannot reach it — and the
    identical-figures check runs first because it is a tuple comparison and it exonerates almost
    every pair before any string matching happens at all.

    `autojunk=False` is not tuning either. The heuristic applies to **seq2 only**, so with it on
    `ratio()` depends on which passage was passed second — and this walk swaps that from what the
    first version did, which silently moved one pair across the threshold. A guard whose verdict
    turns on argument order is not one.
    """
    read = {name: passages(name) for name in DOCUMENTS}
    pairs = 0
    out: list[str] = []
    for left, right in itertools.combinations(DOCUMENTS, 2):
        here, there = read[left], read[right]
        shared = set(here) & set(there)
        pairs += len(shared)
        for a in here:
            if a in shared:
                continue
            figures_a = figures(a)
            matcher = difflib.SequenceMatcher(autojunk=False)
            matcher.set_seq2(a)
            for b in there:
                if b in shared:
                    continue
                matcher.set_seq1(b)
                if (matcher.real_quick_ratio() < SIMILARITY
                        or matcher.quick_ratio() < SIMILARITY
                        or matcher.ratio() < SIMILARITY):
                    continue
                pairs += 1
                if conflict(figures_a, figures(b)):
                    out.append(
                        f"{left}:{here[a]} says {figures_a} and "
                        f"{right}:{there[b]} says {figures(b)} "
                        f"about the same passage: {a[:80]!r}"
                    )
    return pairs, tuple(out)


def divergences() -> tuple[str, ...]:
    """Every near-identical pair of passages whose figures do not match."""
    return _compared()[1]


def test_a_figure_written_into_two_documents_is_the_same_figure_in_both():
    """The failure this exists for: a correction applied to one copy of a claim and not the other.

    It is the recurring defect of this portfolio's own record, and until now the prose documents
    had nothing watching for it.
    """
    bad = divergences()
    assert not bad, "\n".join(bad)


def test_the_comparison_is_actually_finding_pairs_to_compare():
    """A guard that silently matched nothing would make the one above vacuously green.

    The bound, the unit or a renamed document could each empty the population without failing
    anything — the shape `test_vendored_artifacts.py` guards against for the same reason.
    """
    for name in DOCUMENTS:
        assert passages(name), f"{name}: no figure-bearing passages parsed at all"
    compared = _compared()[0]
    assert compared > 20, f"only {compared} passage pairs compared; the population has collapsed"
