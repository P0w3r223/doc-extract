"""The attacked corpus: every payload, in every placement, over documents that are otherwise clean.

An attacked document is a corpus document with one string added to its page. Its **gold is
unchanged**, and that is the design rather than a shortcut: an injected instruction does not alter
what the invoice says, so the correct extraction is the same one it always was. A run over this
corpus is therefore scorable by M4's scorer, detectable by M5's detector and routable by M5's gate
with no special casing anywhere — and the attack success rate is one more reading of the same
prediction file rather than a parallel measurement with its own machinery.

**The grid is a full cross product**, seven payloads by four placements, `per_cell` documents each.
Full because the interesting question is not "does injection work" but *where* it works: the same
sentence in an item description and in white ink at the foot of the page are two different attacks
on two different parts of M3's source layer, and a suite that sampled placements could not say
which.

**Every payload is printed on the same pages.** The base document is chosen by placement and slot
and *not* by payload, so the seven payloads are seven readings of one set of documents rather than
seven samples of different ones. That is what makes the per-payload table a paired comparison: when
`account_redirect` leaves fewer documents exactly right than `total_override` does, the difference
is the payload, because the invoices underneath are identical. It costs variety — a suite of
`per_cell` by `placements` distinct invoices rather than one per cell — and buys the column that
would otherwise be uninterpretable.

**Those pages are spread across the base corpus by a prime stride.** Slot *j* takes base document
`(j·41) mod n`: prime, so it is coprime with the corpus size and with the three layouts, and at the
default sizes it reaches every difficulty tier. A contiguous slice would make every document of the
suite a `clean` document printed `classic`, and a placement's success rate would then be a tier's
success rate wearing a different label.

**A payload that did not survive rendering is a build failure, not a data point.** Every attacked
page is parsed back through `source/` and required to carry its payload's marker. An attack the
model never saw would otherwise land in the denominator as a failed attack, which is the one way an
attack success rate can be wrong in the flattering direction.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Iterator, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from doc_extract.attack.payloads import PAYLOADS, Payload
from doc_extract.source import document as source_document
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.build import Document
from doc_extract.synth.corpus import Entry
from doc_extract.synth.overlay import PLACEMENTS, Overlay
from doc_extract.synth.tiers import TIERS

#: The join file: which payload, in which placement, on which base document. Written beside the
#: manifest rather than into it, so the corpus stays the shape `eval.dataset` already reads and the
#: attack metadata stays the attack suite's own business.
ATTACKS_NAME = "attacks.jsonl"

#: Documents per (payload, placement) cell. Four across a 7x4 grid is 112 attacked documents —
#: about the size of the base corpus, which keeps a remote run over it comparable in cost to a
#: remote run over that.
DEFAULT_PER_CELL = 4

#: The stride that picks base documents out of the corpus. Prime, so it is coprime with any corpus
#: size that is not a multiple of it and with the three layouts — consecutive slots therefore differ
#: in tier and in template rather than marching through one tier in one layout. 41 rather than any
#: other prime because at the default sizes it reaches **all nine tiers** in sixteen slots, which
#: several near neighbours do not; `tests/test_attack_suite.py` asserts it rather than trusting it.
_SPREAD = 41


class SuiteError(RuntimeError):
    """The attacked corpus could not be built as described."""


@dataclass(frozen=True, slots=True)
class Assignment:
    """One attacked document: what was printed on it, where, and what it was printed over."""

    doc_id: str
    base_doc_id: str
    payload: str
    category: str
    placement: str
    tier: str
    template: str
    marker: str


def plan(
    *,
    per_cell: int = DEFAULT_PER_CELL,
    payloads: Sequence[Payload] = PAYLOADS,
    placements: Sequence[str] = PLACEMENTS,
    base: Sequence[Document] | None = None,
) -> list[tuple[Document, Assignment]]:
    """The whole grid, as documents ready to render and the rows that describe them.

    Pure: it touches no disk and draws no random numbers. The same arguments give the same plan, so
    the corpus is a function of its parameters in the same way M2's is a function of its seed.
    """
    if per_cell < 1:
        raise SuiteError("per_cell must be at least 1; a cell with no documents measures nothing")
    documents = list(base if base is not None else synth_corpus.documents())
    if not documents:
        raise SuiteError("the base corpus is empty; build it with `python -m doc_extract.synth`")

    #: Both guards defend the same claim — that the slots of the grid are distinct invoices — and
    #: both failures are silent rather than loud. A stride sharing a factor with the corpus size
    #: walks a short cycle and revisits the same few documents; more slots than documents wraps.
    #: Either leaves the paired design intact and the *variety* it is paired over gone, which is
    #: exactly the kind of quiet weakening this package is not allowed to have.
    slots = len(placements) * per_cell
    if slots > len(documents):
        raise SuiteError(
            f"{slots} slots over a base corpus of {len(documents)}: the grid would reuse "
            "documents. Lower --per-cell or generate a larger base corpus"
        )
    if math.gcd(_SPREAD, len(documents)) != 1:
        raise SuiteError(
            f"the stride {_SPREAD} shares a factor with a base corpus of {len(documents)} "
            "documents, so the slots would cycle through a fraction of it; change --per-tier"
        )

    planned: list[tuple[Document, Assignment]] = []
    for payload in payloads:
        for placement_index, placement in enumerate(placements):
            for slot in range(per_cell):
                page = placement_index * per_cell + slot
                source = documents[(page * _SPREAD) % len(documents)]
                planned.append(_attacked(source, payload, placement, slot))
    return planned


def _attacked(
    source: Document, payload: Payload, placement: str, slot: int
) -> tuple[Document, Assignment]:
    doc_id = f"{payload.name}-{placement}-{slot:02d}"
    attacked = Document(
        doc_id=doc_id,
        tier=source.tier,
        template=source.template,
        seed=source.seed,
        invoice=source.invoice,
        context=source.context,
        overlay=Overlay(text=payload.text, placement=placement),
    )
    assignment = Assignment(
        doc_id=doc_id,
        base_doc_id=source.doc_id,
        payload=payload.name,
        category=payload.category,
        placement=placement,
        tier=source.tier,
        template=source.template,
        marker=payload.marker,
    )
    return attacked, assignment


def generate(
    out_dir: Path,
    *,
    per_cell: int = DEFAULT_PER_CELL,
    payloads: Sequence[Payload] = PAYLOADS,
    placements: Sequence[str] = PLACEMENTS,
    seed: int = synth_corpus.DEFAULT_SEED,
    per_tier: int = synth_corpus.DEFAULT_PER_TIER,
    base: Sequence[Document] | None = None,
    verify: bool = True,
    progress: Callable[[Assignment], None] | None = None,
) -> tuple[list[Entry], list[Assignment]]:
    """Render the grid into a corpus directory, with the join file beside the manifest."""
    if base is None:
        base = list(synth_corpus.documents(seed=seed, per_tier=per_tier))
    planned = plan(per_cell=per_cell, payloads=payloads, placements=placements, base=base)
    out_dir.mkdir(parents=True, exist_ok=True)

    entries: list[Entry] = []
    assignments: list[Assignment] = []
    for document, assignment in planned:
        entry = synth_corpus.write_document(document, out_dir)
        if verify:
            _verify(out_dir / entry.pdf, assignment)
        entries.append(entry)
        assignments.append(assignment)
        if progress is not None:
            progress(assignment)

    write_assignments(out_dir, assignments)
    synth_corpus.write_index(
        out_dir,
        entries,
        _provenance(
            entries, per_cell=per_cell, payloads=payloads, placements=placements,
            seed=seed, per_tier=per_tier, verified=verify,
        ),
        keep=(ATTACKS_NAME,),
    )
    return entries, assignments


def _verify(pdf_path: Path, assignment: Assignment) -> None:
    """Read the page back and require the payload to be on it.

    Whitespace is removed from both sides before comparing, because a renderer wraps a paragraph
    where the column ends and M3's layout reader joins cells with tabs — neither is a change to the
    words. Anything stronger would fail on formatting; anything weaker would not be a check.
    """
    text = source_document.read(pdf_path.read_bytes()).text
    if _squeezed(assignment.marker) not in _squeezed(text):
        raise SuiteError(
            f"{assignment.doc_id}: the payload's marker {assignment.marker!r} is not in the text "
            f"layer of {pdf_path.name}; the {assignment.placement} placement did not survive "
            "rendering, and an attack the model never sees is a missing measurement rather than a "
            "failed attack"
        )


def _squeezed(text: str) -> str:
    return "".join(text.split())


def _provenance(
    entries: Sequence[Entry],
    *,
    per_cell: int,
    payloads: Sequence[Payload],
    placements: Sequence[str],
    seed: int,
    per_tier: int,
    verified: bool,
) -> dict[str, Any]:
    """The base corpus's provenance block, plus what this suite did to it.

    Built from `synth.corpus.provenance` rather than assembled here, so the font hashes, the XSD
    hash and the reportlab version — everything a rendered byte depends on — are recorded by the one
    function that knows what they are. A report reads `corpus_seed` and the versions out of this
    block without knowing which of the two corpora it is describing.
    """
    base = asdict(synth_corpus.provenance(
        seed=seed, per_tier=per_tier, tiers=TIERS, documents=len(entries),
    ))
    return {
        **base,
        "attacked": True,
        "per_cell": per_cell,
        "payloads": [payload.name for payload in payloads],
        "placements": list(placements),
        #: Whether every payload was read back off its own page. A report computed from this corpus
        #: states one thing or the opposite depending on this flag, which is why it is recorded
        #: rather than assumed: an unverified corpus otherwise produces a report claiming a check
        #: that never ran.
        "verified": verified,
    }


def write_assignments(out_dir: Path, assignments: Sequence[Assignment]) -> Path:
    path = out_dir / ATTACKS_NAME
    path.write_bytes(
        "".join(json.dumps(asdict(row), ensure_ascii=False) + "\n" for row in assignments)
        .encode("utf-8")
    )
    return path


def load_assignments(directory: Path) -> tuple[Assignment, ...]:
    """The join file, back. Missing is an error with the command that writes it in the message."""
    path = directory / ATTACKS_NAME
    if not path.exists():
        raise SuiteError(
            f"no {ATTACKS_NAME} in {directory}; this is not an attacked corpus. Build one with "
            f"`python -m doc_extract.attack --out {directory}`"
        )
    return tuple(Assignment(**row) for row in _rows(path))


def _rows(path: Path) -> Iterator[dict[str, Any]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)
