"""M6's attacked pages, photographed. The composition the trust-boundary ADR named and did not run.

Both halves already existed: `attack/suite.py` prints a payload on a page and `degrade/page.py`
turns a page into a picture of itself. Composing them answers a question neither could — **which
channel does an injected instruction actually reach a reader by, once the document has been
scanned?** — and it answers it about the pipeline an accounts-payable team is most likely to be
running, because the invoices that arrive as photographs are exactly the ones nobody controls.

**The gold does not move, twice over.** An injected instruction does not change what the invoice
states (M6) and neither does a scanner (M7c), so the correct extraction of a scanned attacked
document is the one it always was. The scorer, the detector, the gate and the attack judge all run
over this corpus unchanged, which is what keeps a composition from needing a third measurement
pipeline.

**Both factors are crossed, not sampled.** Every payload meets every placement meets every rung, on
base documents chosen by placement and slot alone — so the same invoice appears at all three rungs
under all seven payloads. A per-rung difference is therefore the *legibility of the page*, paired
document for document, in the same sense M6's per-payload table is paired.

**A payload reaches a reader by one of two channels, and they fail differently.** The text layer is
what M3 reads; the image is what a vision model reads. `Reach` records both per document, measured
without a model:

* **the text layer** — parse the scanned page back through `source/` and look for the marker. On a
  rung with no text layer this is `False` for every document, and that is blindness rather than a
  defence, which is the single most important thing this module's report has to say.
* **the image** — rasterise the attacked page and the *unattacked* page it was made from, at that
  rung's own resolution and through that rung's own optics, and compare the bytes. Identical images
  mean the overlay left no mark, so no reader that looks at the page can see it. That is not a
  hypothetical: M6's `invisible` placement is white ink, it contributes no pixel, and a scan erases
  it completely. The measurement is what turns that from an argument into a number.

Because the two documents share a seed, they meet the same grain and the same skew, so a difference
between their images is the ink and never the sensor.

**What is still a build failure is what was a build failure before.** The payload must be in the
text layer of the page as *printed*, before any scanner touches it — otherwise the placement did not
render and the document is a missing measurement rather than a surviving attack. What the scan then
does to it is the finding, so it is recorded and never raised.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Sequence
from dataclasses import asdict, dataclass, replace
from importlib import metadata
from pathlib import Path
from typing import Any

#: The direction this composition is allowed to run in: **`degrade` may import `attack`'s pure
#: planner, and nothing under `attack/` imports anything from `degrade/`.** The attack suite is
#: about what an attacker prints; a scanner is about what survives being photographed, and a suite
#: that had to know about rungs would make every clean attacked document depend on a rasteriser.
from doc_extract.attack.payloads import PAYLOADS, Payload
from doc_extract.attack.suite import ATTACKS_NAME, Assignment, SuiteError, write_assignments
from doc_extract.attack.suite import plan as attack_plan
from doc_extract.degrade import page as scanner
from doc_extract.degrade.rungs import RUNGS, Rung
from doc_extract.source import document as source_document
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth import render as synth_render
from doc_extract.synth.build import Document
from doc_extract.synth.corpus import Entry
from doc_extract.synth.overlay import PLACEMENTS
from doc_extract.synth.tiers import TIERS

#: Which channel each payload survived by. Beside the manifest and the join file rather than inside
#: either, for the reason `attacks.jsonl` sits beside the manifest: the corpus stays the shape
#: `eval.dataset` already reads, and this package's own bookkeeping stays this package's.
REACH_NAME = "reach.jsonl"

#: Documents per (payload, placement) cell *before* the rungs multiply them. Two rather than M6's
#: four because the third factor triples the corpus: 7 payloads x 4 placements x 2 x 3 rungs is 168
#: documents, against 112 for M6's grid, and every one of the 84 cells is filled twice.
DEFAULT_PER_CELL = 2


@dataclass(frozen=True, slots=True)
class Reach:
    """One attacked scan, and the channels its payload came through.

    Deliberately two booleans rather than one verdict. A payload that is on the image and not in the
    text layer is invisible to M3 and plain to a vision model; one that is in the text layer and not
    on the image is the reverse, and is what M6's `invisible` placement is on an unscanned page.
    Collapsing them would erase exactly the distinction this corpus exists to draw.
    """

    doc_id: str
    payload: str
    placement: str
    rung: str
    #: The marker is in the text `source/` reads off the scanned page.
    in_text_layer: bool
    #: The overlay changed at least one pixel of the page as the scanner leaves it.
    on_the_image: bool

    @property
    def reaches_nobody(self) -> bool:
        """Neither channel carries it, so no reader of this document can be attacked by it."""
        return not self.in_text_layer and not self.on_the_image


def plan(
    *,
    per_cell: int = DEFAULT_PER_CELL,
    payloads: Sequence[Payload] = PAYLOADS,
    placements: Sequence[str] = PLACEMENTS,
    rungs: Sequence[Rung] = RUNGS,
    base: Sequence[Document] | None = None,
) -> list[tuple[Document, Rung, Assignment]]:
    """M6's grid crossed with the rungs. Pure — no disk, no random numbers, no rasterising.

    The document keeps the layout it has to be printed in; the assignment's `template` becomes the
    **rung**, which is the convention `degrade/corpus.py` already set and the one `eval.report` and
    `attack.report` both read a "per template" table out of. What the page looks like is one column
    and this corpus varies which scanner it went through, so that is the column it goes in. The
    underlying layout is recorded once, in the provenance block, rather than per row.
    """
    if not rungs:
        raise SuiteError(
            "no rungs: a scanned corpus with no scanner is the corpus it was made from"
        )
    crossed: list[tuple[Document, Rung, Assignment]] = []
    for document, assignment in attack_plan(
        per_cell=per_cell, payloads=payloads, placements=placements, base=base
    ):
        for rung in rungs:
            doc_id = f"{assignment.doc_id}-{rung.name}"
            crossed.append((
                replace(document, doc_id=doc_id),
                rung,
                replace(assignment, doc_id=doc_id, template=rung.name),
            ))
    return crossed


def generate(
    out_dir: Path,
    *,
    per_cell: int = DEFAULT_PER_CELL,
    payloads: Sequence[Payload] = PAYLOADS,
    placements: Sequence[str] = PLACEMENTS,
    rungs: Sequence[Rung] = RUNGS,
    seed: int = synth_corpus.DEFAULT_SEED,
    per_tier: int = synth_corpus.DEFAULT_PER_TIER,
    base: Sequence[Document] | None = None,
    verify: bool = True,
    progress: Callable[[Assignment, Reach], None] | None = None,
) -> tuple[list[Entry], list[Assignment], list[Reach]]:
    """Render the crossed grid into a corpus directory, with the join file and the reach file."""
    if base is None:
        base = list(synth_corpus.documents(seed=seed, per_tier=per_tier))
    crossed = plan(
        per_cell=per_cell, payloads=payloads, placements=placements, rungs=rungs, base=base,
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    entries: list[Entry] = []
    assignments: list[Assignment] = []
    reaches: list[Reach] = []
    layouts: dict[str, str] = {}
    clean = _CleanPages()
    for document, rung, assignment in crossed:
        layouts[assignment.doc_id] = document.template
        printed = synth_render.render(document).data
        if verify:
            _verify_printed(printed, assignment)
        scan = scanner.scan(printed, rung, seed=document.seed)
        #: The manifest's view has the rung where its `template` column is, and the page was drawn
        #: from the layout view above. Keeping the two objects apart is what stops a page from
        #: being printed in a layout called `scanned` — `degrade/corpus.py` makes the same split.
        entries.append(synth_corpus.write_document(
            replace(document, template=rung.name), out_dir, draw=_already(scan),
        ))
        reach = _reach(document, rung, assignment, scan=scan, clean=clean)
        assignments.append(assignment)
        reaches.append(reach)
        if progress is not None:
            progress(assignment, reach)

    write_assignments(out_dir, assignments)
    write_reaches(out_dir, reaches)
    synth_corpus.write_index(
        out_dir,
        entries,
        _provenance(
            entries, per_cell=per_cell, payloads=payloads, placements=placements, rungs=rungs,
            seed=seed, per_tier=per_tier, verified=verify, layouts=layouts,
        ),
        keep=(ATTACKS_NAME, REACH_NAME),
    )
    return entries, assignments, reaches


def _already(scan: scanner.Scan) -> Callable[[Document], scanner.Scan]:
    """A `Draw` that returns a page already drawn.

    The scan has to happen before the manifest row is written, because the reach measurement reads
    it — and it must not happen twice, because rasterising is the expensive half of this build.
    """
    return lambda _: scan


class _CleanPages:
    """The unattacked page each attacked one is compared against, rendered and damaged once.

    A base document meets seven payloads at three rungs, and the picture it makes without any of
    them is the same picture every time — so at the default sizes this is 24 rasterisations rather
    than 168.

    **The key is the base document, not the attacked one.** `plan` has already rewritten `doc_id` to
    `{payload}-{placement}-{slot}-{rung}`, which is unique per row, so keying on the document that
    arrives here would give every row its own entry and the cache would never return a hit. Nothing
    the clean page depends on — the invoice, the context, the layout, the seed — differs between two
    attacked documents built from one base, and the renderer never reads `doc_id`.
    """

    def __init__(self) -> None:
        self._pages: dict[tuple[str, str], tuple[bytes, ...]] = {}

    def of(self, document: Document, rung: Rung, *, base_doc_id: str) -> tuple[bytes, ...]:
        key = (base_doc_id, rung.name)
        if key not in self._pages:
            unattacked = replace(document, doc_id=base_doc_id, overlay=None)
            self._pages[key] = scanner.damaged(
                synth_render.render(unattacked).data, rung, seed=document.seed
            )
        return self._pages[key]


def _reach(
    document: Document,
    rung: Rung,
    assignment: Assignment,
    *,
    scan: scanner.Scan,
    clean: _CleanPages,
) -> Reach:
    """The two channels, each measured against what it actually is rather than inferred.

    The text channel is read off the scanned document, because that is the file a reader is handed.
    The image channel compares the attacked page with the unattacked one **through the same
    scanner** — same resolution, same skew, same seeded grain, same quantiser — so the only thing
    that can differ between them is the overlay. The attacked side is the images `scan` already
    produced rather than a second rasterisation of the same page: recomputing them would be the
    same bytes at twice the cost, and it would put a second definition of "what the scanner leaves"
    beside the one that was written to disk.
    """
    return Reach(
        doc_id=assignment.doc_id,
        payload=assignment.payload,
        placement=assignment.placement,
        rung=rung.name,
        in_text_layer=(
            _squeezed(assignment.marker) in _squeezed(source_document.read(scan.data).text)
        ),
        on_the_image=(
            scan.images != clean.of(document, rung, base_doc_id=assignment.base_doc_id)
        ),
    )


def _verify_printed(printed: bytes, assignment: Assignment) -> None:
    """The payload has to be on the page *before* the scanner, or the placement did not render.

    This is M6's build-time guarantee, applied where it still means what it meant: an attack the
    corpus never carried would sit in the denominator as a failed attack. What the scan then does to
    it is the measurement, so it is recorded in `Reach` and never raised here — a rung that erases a
    payload has produced a result, not a build error.
    """
    text = _squeezed(source_document.read(printed).text)
    if _squeezed(assignment.marker) not in text:
        raise SuiteError(
            f"{assignment.doc_id}: the payload's marker {assignment.marker!r} is not in the text "
            f"layer of the page as printed, before any scanner touched it; the "
            f"{assignment.placement} placement did not render, and an attack the corpus never "
            "carried is a missing measurement rather than a failed attack"
        )


def _squeezed(text: str) -> str:
    return "".join(text.split())


def _provenance(
    entries: Sequence[Entry],
    *,
    per_cell: int,
    payloads: Sequence[Payload],
    placements: Sequence[str],
    rungs: Sequence[Rung],
    seed: int,
    per_tier: int,
    verified: bool,
    layouts: dict[str, str],
) -> dict[str, Any]:
    """M2's block, plus what M6 did to the page and what M7 did to the picture of it."""
    base = asdict(synth_corpus.provenance(
        seed=seed, per_tier=per_tier, tiers=TIERS, documents=len(entries),
    ))
    return {
        **base,
        "renderer": "scanned",
        "attacked": True,
        "per_cell": per_cell,
        "payloads": [payload.name for payload in payloads],
        "placements": list(placements),
        "rungs": [asdict(rung) for rung in rungs],
        #: Which layout each document was printed in, since its `template` column is the rung. The
        #: rotation is M2's and is what stops a per-rung drop from being a per-layout drop.
        "layouts": layouts,
        #: Whether every payload was read back off its own page before it was scanned. A report
        #: computed from this corpus states one thing or the opposite depending on this flag.
        "verified": verified,
        "pypdfium2_version": _version("pypdfium2"),
        "pillow_version": _version("pillow"),
    }


def _version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:  # pragma: no cover — only from a bare checkout
        return "unknown"


def write_reaches(out_dir: Path, reaches: Sequence[Reach]) -> Path:
    path = out_dir / REACH_NAME
    path.write_bytes(
        "".join(json.dumps(asdict(row), ensure_ascii=False) + "\n" for row in reaches)
        .encode("utf-8")
    )
    return path


def load_reaches(directory: Path) -> tuple[Reach, ...]:
    """The reach file, back. Missing is an error naming the command that writes it."""
    path = directory / REACH_NAME
    if not path.exists():
        raise SuiteError(
            f"no {REACH_NAME} in {directory}; this is not a scanned attacked corpus. Build one "
            f"with `python -m doc_extract.degrade --attacked --out {directory}`"
        )
    return tuple(Reach(**row) for row in _rows(path))


def _rows(path: Path) -> Iterator[dict[str, Any]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)
