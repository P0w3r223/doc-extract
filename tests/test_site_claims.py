"""What the page *says* about its figures, checked against the figures.

`test_site_committed` renders the page and byte-diffs the result against `docs/index.html`. That
establishes one thing — the committed bytes are not stale — and it cannot establish more, because
both sides of that comparison come out of `build_index`. A sentence the generator itself gets wrong
is identical on both sides, so a claim that is false about the artifacts stays green forever.

Two were, until `9f4bd21`:

* **A KPI tile read `5 / 7` &mdash; &ldquo;Milestones built&rdquo;**, with the note *the gate is
  measured; injection and the real set are not*. The same page's eyebrow said milestones 1&ndash;6
  of 7, the table at its foot marked M3&ndash;M7 `built`, and the injection grid the note called
  unmeasured sat two hundred lines below it. The tile was a project-management number typed into a
  row of measurements, and nothing derived it from anything.
* **A sentence read *&ldquo;The two payloads the arithmetic never sees are …&rdquo;*** followed by
  the names, interpolated from `injection_study`. The list had grown to three and the word had not.

The shape is the same in both: a figure computed from an artifact, and the words around it typed by
hand. This module pins the words. It is the discipline the sibling `apply-scout` wrote up in
ADR-0012 — *the page quotes the artifacts, it never retypes them* — narrowed to the surface that
actually drifted here, which is number **words** rather than digits. That ADR names words as its
own blind spot, so a digit tokeniser copied across would have missed both of the defects above.

**What this does not establish**, stated plainly because the rule is easier to overclaim than to
enforce. It covers cardinals attached to a noun naming a set the repository computes, and the four
headline tiles. A page can still name the wrong cause in prose, describe a measurement it does not
carry, or contradict itself between two paragraphs that quote no count &mdash; and nothing here will
notice. `test_a_kpi_value_is_computed_rather_than_typed` reads the tile's *value*; the tile's
*label* and *note* are prose, and the note was the more misleading half of the defect above — it is
checked by reading, not here.
"""

from __future__ import annotations

import pathlib
import re
import sys

import pytest

from doc_extract.degrade.rungs import RUNGS

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "index.html"

#: The generator lives in `docs/`, which is not a package and not on the path.
sys.path.insert(0, str(ROOT / "docs"))

#: English, not a project artifact — deliberately a second transcription rather than an import of
#: `build_index._WORDS`. A test that spells the number with the same table the generator spells it
#: with asserts that one dictionary equals itself; this one asserts that the word beside a computed
#: list is the word for how long that list is.
SPELLED = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
}
CARDINALS = {word: value for value, word in SPELLED.items()}


@pytest.fixture(scope="module")
def corpus():
    import build_index

    return list(build_index.documents())


@pytest.fixture(scope="module")
def study(corpus):
    """M6's grid, recomputed from the committed attacked run — what every claim below quotes."""
    import build_index

    computed = build_index.injection_study(corpus)
    if computed is None:  # pragma: no cover — a checkout without `results/attack-gullible`
        pytest.skip("no committed run over an attacked corpus in this checkout")
    return computed


def _attacking(study) -> int:
    """How many payloads ask for something, counted off `PAYLOADS` rather than read off the study.

    `injection_study` publishes this as `attacking` and the fourth tile is rendered from it, so
    quoting that key back would assert that the generator agrees with itself. Counted here from the
    payload definitions instead: the page's claim then has a source one step further out than the
    dictionary the page was built from.
    """
    import build_index

    return sum(1 for name in study["rows"] if not build_index.PAYLOADS[name].harmless)


@pytest.fixture(scope="module")
def committed():
    if not PAGE.exists():  # pragma: no cover — a checkout that never built the site
        pytest.skip("the site has not been built in this checkout")
    return PAGE.read_text(encoding="utf-8")


# --------------------------------------------------------------------------------------------
# The headline tiles
# --------------------------------------------------------------------------------------------

_KPI_VALUE = re.compile(r'<div class="kpi-value">(.*?)</div>', re.DOTALL)
#: A `str.format` replacement field. `TEMPLATE` is a format string, so a literal brace in it is
#: doubled — `{{` and `}}` are stripped before looking for a field, or the CSS would read as one.
_FIELD = re.compile(r"\{[a-z_][a-z0-9_]*\}")


def test_a_kpi_value_is_computed_rather_than_typed():
    """The four headline figures must be interpolated. One of them was not, and it was wrong.

    Checked against `TEMPLATE` rather than against the rendered page, because that is where the
    distinction lives: on the page a typed `5 / 7` and a computed `3 / 6` are both just digits, and
    no test that reads the output can tell which of them had an upstream. In the template, one is a
    replacement field and the other is not.

    A tile is the page's loudest claim and the one a reader takes away, so this is the one region
    where a bare digit is a defect on sight. The rule is not extended to the notes below the
    values: those legitimately carry `XSD 1.0`, and a rule with an exemption list for version
    numbers would be a rule about spelling rather than about provenance.
    """
    import build_index

    values = _KPI_VALUE.findall(build_index.TEMPLATE)

    assert len(values) == 4, (
        f"{len(values)} KPI tiles, not 4 — move this count if the row grew, but read the new "
        "tile first: a tile is a headline figure and it needs a source"
    )
    for value in values:
        single = value.replace("{{", "").replace("}}", "")
        assert _FIELD.search(single), (
            f"the KPI value {value.strip()!r} is typed into the template, not computed from the "
            "repository — a hand-typed headline has no artifact to go stale against, which is how "
            "`5 / 7 milestones built` survived on a page whose own table said seven of seven"
        )
        literal = _FIELD.sub("", single)
        assert not any(character.isdigit() for character in literal), (
            f"the KPI value {value.strip()!r} mixes a computed figure with a typed one"
        )


_TILE = re.compile(
    r'<li class="kpi">\s*<div class="kpi-value">(.*?)</div>\s*'
    r'<div class="kpi-label">(.*?)</div>\s*<div class="kpi-note">(.*?)</div>',
    re.DOTALL,
)


def test_the_ratio_tile_counts_the_payloads_the_arithmetic_never_sees(committed, study):
    """The one tile shaped `n / m` is the injection study's headline, and must equal it.

    Found by its shape rather than by its position, so reordering the row does not silently move
    what is asserted onto a different tile. The shape is what the stale tile had too — `5 / 7` and
    `3 / 6` are the same shape — which is exactly why locating it this way makes the test red on
    the page that carried the defect rather than merely absent from it.
    """
    tiles = _TILE.findall(committed)
    assert len(tiles) == 4, "the KPI row is not four tiles — check the markup, not the numbers"

    ratios = [(value.strip(), label.strip()) for value, label, _ in tiles
              if re.fullmatch(r"\d+\s*/\s*\d+", value.strip())]

    assert len(ratios) == 1, (
        f"{len(ratios)} tiles read as `n / m`; this test asserts against exactly one"
    )
    value, label = ratios[0]
    attacking = _attacking(study)
    expected = f"{len(study['invisible'])} / {attacking}"
    assert value == expected, (
        f"the {label!r} tile reads {value!r}; the attacked run counts {expected} — "
        f"{len(study['invisible'])} payloads that succeed with the arithmetic silent, of "
        f"{attacking} that ask for anything"
    )


# --------------------------------------------------------------------------------------------
# The injection section's prose
# --------------------------------------------------------------------------------------------

def _section(study) -> str:
    """The injection section as the page carries it, tied to the page rather than assumed.

    `build()` wraps every table in a scroll box after assembly, so the section is on the page in
    its wrapped form. Asserting that form is present is what makes the sentences below claims
    about the *published* page rather than about a string this test just built.
    """
    import build_index

    return build_index._scrollable_tables(build_index.injection_section(study))


def test_the_invisible_payload_sentence_counts_the_names_it_lists(committed, study):
    """`The three payloads … are a, b, c` — the word, the list, and the study, all one number.

    This is the sentence that drifted. The names came from `injection_study["invisible"]`; the
    word did not, so when a third payload started slipping past the arithmetic the list grew and
    the sentence went on saying *two*. Both halves are checked against each other and against the
    study, because a sentence whose word matched a list that no longer matched the run would be
    a second version of the same failure.
    """
    section = _section(study)
    assert section in committed, (
        "the injection section on docs/index.html is not what the generator renders — "
        "re-run `python docs/build_index.py`"
    )

    match = re.search(
        r"<strong>The (\w+) payloads the arithmetic never sees are (.*?)</strong>",
        section,
        re.DOTALL,
    )
    assert match is not None, (
        "the sentence naming the payloads the arithmetic is blind to is not on the page, or was "
        "reworded past this pattern — it is this page's finding, so re-point the test rather than "
        "deleting it"
    )
    word, listed = match.group(1), re.findall(r"<code>(.*?)</code>", match.group(2))

    assert listed == list(study["invisible"]), (
        f"the sentence names {listed}; the study finds {list(study['invisible'])}"
    )
    assert word == SPELLED[len(listed)], (
        f"the sentence says {word!r} and then lists {len(listed)} payloads "
        f"({', '.join(listed)}) — the count is typed and the list is computed"
    )


def test_the_grid_is_introduced_by_a_headcount_of_its_own_rows(committed, study):
    """*Seven payloads — six that ask for something and one control* must decompose the grid.

    Unlike the two above, this sentence was never wrong: the payload set has not moved since it
    was written. It is pinned because it is the same construction that failed twice on this page —
    three cardinals typed into prose, standing for a set the table directly below them enumerates —
    and because it is the sentence a seventh attacking payload would falsify first.

    The table is counted as well as the study, so the claim is anchored to what the reader can see
    under it rather than only to what the generator knows.
    """
    section = _section(study)
    assert section in committed

    match = re.search(
        r"<p>(\w+) payloads &mdash;\s+(\w+) that ask for something and (\w+) control",
        section,
    )
    assert match is not None, (
        "the sentence that introduces the injection grid was reworded past this pattern"
    )
    total, asking, control = (CARDINALS.get(word.lower()) for word in match.groups())

    rows = len(study["rows"])
    attacking = _attacking(study)
    assert (total, asking, control) == (rows, attacking, rows - attacking), (
        f"the sentence reads {match.group(0)!r}; the run carries {rows} payloads, {attacking} of "
        f"which ask for something and {rows - attacking} of which are controls"
    )

    body = re.search(r"<tbody>(.*?)</tbody>", section, re.DOTALL)
    assert body is not None and body.group(1).count("<tr>") == rows, (
        "the grid under that sentence prints a different number of rows than the sentence claims"
    )


# --------------------------------------------------------------------------------------------
# The class, over the whole page
# --------------------------------------------------------------------------------------------

#: Nouns on this page that name a set something in the repository counts, and where that count
#: lives. A cardinal written in front of one of these is a claim about a committed artifact, so it
#: is checked; a cardinal in front of anything else ("the two columns", "one question") is rhetoric
#: and is left alone. Keyed by the singular, because the page uses both.
#:
#: A value is a *set* of admissible counts rather than one number, because a page may legitimately
#: quantify a subset it computes — "the three payloads the arithmetic never sees" is as sourced as
#: "seven payloads". A subset the generator does *not* compute is precisely the case this rule is
#: meant to refuse: publishing it means teaching `injection_study` to count it, which is the same
#: friction ADR-0012 imposes on a figure and for the same reason.
def _counted_sets(corpus, study) -> dict[str, set[int]]:
    import build_index

    rows = len(study["rows"])
    attacking = _attacking(study)
    return {
        "tier": {len(build_index.TIERS)},
        "layout": {len({document.template for document in corpus})},
        "rung": {len(RUNGS)},
        "payload": {rows, attacking, rows - attacking, len(study["invisible"])},
        #: The page says *places*, not *placements* — and the dead-entry check above is what said
        #: so: a `placement` key was written here first and failed for having nothing to cover.
        "place": {int(study["placements"])},
    }


def _cardinal_claims(page: str, nouns) -> list[tuple[str, str, int]]:
    """Every `<cardinal> <noun>` on the page, cardinal resolved to an integer.

    `\\s+` rather than a space: the generator folds its prose at column 100, so a claim is as
    likely to be split across a newline as not — `two of the three\\nrungs` is one of them, and a
    pattern that required a single space would quietly stop covering it.
    """
    pattern = re.compile(
        rf"\b({'|'.join(CARDINALS)}|\d+)\s+({'|'.join(f'{noun}s?' for noun in nouns)})\b",
        re.IGNORECASE,
    )
    claims = []
    for match in pattern.finditer(page):
        word, noun = match.group(1).lower(), match.group(2).lower().rstrip("s")
        value = CARDINALS[word] if word in CARDINALS else int(word)
        claims.append((match.group(0), noun, value))
    return claims


def test_every_counted_claim_on_the_page_matches_the_set_it_counts(committed, corpus, study):
    """The class the two defects belonged to, read over the whole page rather than per sentence.

    Per-claim assertions cover the claims somebody remembered to assert, and the sentence that went
    stale here was a supporting one rather than a headline. This reads the assembled page: any
    cardinal, anywhere, in front of a noun naming a set the repository counts.

    Deliberately a matcher over words as well as digits. The equivalent rule in the sibling project
    tokenises digits and names words as its known blind spot — and both of the defects this file
    exists for were words, or a digit pair that no artifact produced.
    """
    expected = _counted_sets(corpus, study)
    claims = _cardinal_claims(committed, expected)

    #: A rule that matches nothing passes. Each noun is required to appear at least once, so a
    #: rewording that drops the last sentence using one fails here instead of silently retiring
    #: that noun's cover — the same argument the neighbouring file makes for its dead-exemption
    #: check.
    seen = {noun for _, noun, _ in claims}
    assert seen == set(expected), (
        f"nothing on the page counts: {', '.join(sorted(set(expected) - seen))} — either the "
        "prose moved and this map should follow it, or the entry is dead and should be dropped"
    )

    wrong = [
        (phrase, noun, value, sorted(expected[noun]))
        for phrase, noun, value in claims
        if value not in expected[noun]
    ]
    assert not wrong, "the page counts something the repository counts differently:\n" + "\n".join(
        f"  {phrase!r} — the repository counts {allowed} {noun}(s), not {value}"
        for phrase, noun, value, allowed in wrong
    )
