"""The page as pixels, for a reader with no text layer to read.

`words.py` asks the PDF what it says; this asks what it *looks like*. The two are different
questions and M7 is where they stop having the same answer: a scanned invoice carries no text layer
at all, so everything built on `words` returns nothing and the only remaining reader is one that
sees the page.

One implementation, in one place, used twice — `degrade/` rasterises a rendered page in order to
damage it, and `eval/` rasterises a corpus page in order to send it to a model. Two copies would be
two chances for the corpus a study reports on and the corpus a model was shown to drift apart.

**A page is rendered grey.** The corpus prints nothing that carries meaning in hue, and a colour
bitmap would triple the bytes on a path that already sends every page over the network.

**The long edge is capped before a request, not after.** An image larger than the model's own
ceiling is resized by the API, so sending one buys nothing and is billed for the upload; the cap is
named here so the page a study reports on is the page the model was shown.
"""

from __future__ import annotations

import pypdfium2 as pdfium
from PIL import Image

#: A scanner's default, and the resolution the degraded corpus is built at unless a rung says
#: otherwise.
DEFAULT_DPI = 200.0

#: Points per inch, as PDF counts them. Named because `dpi / POINTS_PER_INCH` appears wherever a
#: resolution becomes a scale factor, and a bare 72 in that expression reads as a magic number.
POINTS_PER_INCH = 72.0

#: The longest edge a page image is sent to a model with. Anthropic resizes anything larger before
#: it is tokenised, so a bigger upload costs bandwidth and changes nothing the model sees.
VISION_LONG_EDGE = 1568


def pages(data: bytes, *, dpi: float = DEFAULT_DPI) -> tuple[Image.Image, ...]:
    """Every page of a PDF as a greyscale bitmap, in printed order."""
    pdf = pdfium.PdfDocument(data)
    try:
        return tuple(
            pdf[index].render(scale=dpi / POINTS_PER_INCH).to_pil().convert("L")
            for index in range(len(pdf))
        )
    finally:
        pdf.close()


def page_sizes(data: bytes) -> tuple[tuple[float, float], ...]:
    """Each page's size in points, so a rewrapped page keeps the shape of the one it came from."""
    pdf = pdfium.PdfDocument(data)
    try:
        return tuple(tuple(pdf[index].get_size()) for index in range(len(pdf)))  # type: ignore[misc]
    finally:
        pdf.close()


def for_vision(data: bytes, *, long_edge: int = VISION_LONG_EDGE) -> tuple[Image.Image, ...]:
    """The pages at the largest size worth sending: capped on the long edge, never enlarged.

    Never enlarged because upscaling a 150 dpi scan to the ceiling would hand the model a page the
    corpus does not contain — a sharper one would be dishonest, and a blurrier one is what a real
    ingest pipeline would receive anyway.
    """
    return tuple(_capped(page, long_edge) for page in pages(data, dpi=_dpi_for(data, long_edge)))


def _dpi_for(data: bytes, long_edge: int) -> float:
    """The resolution that puts the tallest page's long edge on the cap, and no higher."""
    sizes = page_sizes(data)
    if not sizes:  # pragma: no cover — pdfium refuses to open a PDF with no pages
        return DEFAULT_DPI
    longest = max(max(width, height) for width, height in sizes)
    return min(DEFAULT_DPI, long_edge * POINTS_PER_INCH / longest)


def _capped(image: Image.Image, long_edge: int) -> Image.Image:
    if max(image.size) <= long_edge:
        return image
    scale = long_edge / max(image.size)  # pragma: no cover — `_dpi_for` already holds the size down
    return image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        resample=Image.Resampling.LANCZOS,
    )
