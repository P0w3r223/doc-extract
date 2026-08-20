"""The three rungs of legibility, as data.

M2's tiers vary what an invoice *means* — grosz rounding, corrections, reverse charge, two pages —
and M7's foreign corpus varies what a page *says* it with. Neither varies whether the page can be
read at all, and that is the remaining reason a frontier model scores 100 % on this corpus: every
document ships a perfect text layer, because reportlab wrote it.

A rung removes that. Each one is a scanner: the page is rasterised at a stated resolution, put
through the optics of a real one, and written back as an image. What separates the three is a single
question each, and they are ordered so that a drop between two of them is attributable:

* **`searchable`** keeps a text layer. The image is degraded and the words are re-emitted invisibly
  over it, at the boxes they occupied — which is what a searchable PDF from an OCR engine is, with
  the OCR assumed perfect. It is the **ceiling** for that pipeline, and the control that separates
  "the image is worse" from "the text layer is gone": anything reading text scores here exactly what
  it scored on the clean corpus, or the degradation reached something it should not have.
* **`rasterised`** removes the text layer and nothing else. A clean 200 dpi bitmap of the same
  page — nothing is harder to *see*, and everything that read the text layer is now blind. It
  isolates the loss of the text layer from the loss of legibility, which no single "scan" rung
  could.
* **`scanned`** is the one a supplier actually emails: 150 dpi, off-square on the platen, grain from
  the sensor, and JPEG at a quality nobody chose deliberately.

The numbers below are deliberately mild. A rung that made the page unreadable would measure the
degradation rather than the reader, and "an illegible page cannot be extracted" is not a finding.
`tests/test_degrade_page.py` holds them to that: every gold value must still be legible on the
`searchable` rung, which is the only one whose text this project can check without a model.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rung:
    """One scanner, described by what it does to a page rather than by how it is implemented."""

    name: str
    #: Resolution the page is rasterised at. 200 dpi is a scanner's default; 150 is a fax's.
    dpi: float
    #: Rotation in degrees. A page is never square on the platen, and a tenth of a degree is enough
    #: to break an assumption that a printed row shares a y coordinate.
    skew_degrees: float
    #: How much uniform sensor noise is blended in, 0 to 1.
    grain: float
    #: Gaussian blur radius in pixels — the optics, not the paper.
    blur: float
    #: JPEG quality. The artefacts around glyph edges are the characteristic damage of a scan.
    quality: int
    #: Whether the words survive as a text layer over the image.
    text_layer: bool
    description: str


SEARCHABLE = Rung(
    name="searchable",
    dpi=200,
    skew_degrees=0.35,
    grain=0.05,
    blur=0.4,
    quality=60,
    text_layer=True,
    description="a scan that was OCR'd, with the OCR assumed perfect — the ceiling for that path",
)

RASTERISED = Rung(
    name="rasterised",
    dpi=200,
    skew_degrees=0.0,
    grain=0.0,
    blur=0.0,
    quality=92,
    text_layer=False,
    description="a clean bitmap of the same page: nothing harder to see, and no text layer",
)

SCANNED = Rung(
    name="scanned",
    dpi=150,
    skew_degrees=0.8,
    grain=0.11,
    blur=0.8,
    quality=45,
    text_layer=False,
    description="what a supplier emails: off-square, grainy, and JPEG at a quality nobody chose",
)

RUNGS: tuple[Rung, ...] = (SEARCHABLE, RASTERISED, SCANNED)

BY_NAME: dict[str, Rung] = {rung.name: rung for rung in RUNGS}

#: The names, in the order a report should read them: most legible first.
TEMPLATES: tuple[str, ...] = tuple(rung.name for rung in RUNGS)
