"""A rendered page, put through a scanner and written back as a PDF.

The input is M2's own page, not a second renderer: `foreign/` already varies what a page says, and
varying both at once would leave a drop attributable to neither. What varies here is legibility and
nothing else, which is why the underlying layout, the fonts and the invoice are M2's exactly.

**The text layer is rebuilt, not preserved.** A rasterised page has none — that is the point of the
rung — and `searchable` puts one back the way an OCR engine does: every word drawn invisibly (render
mode 3) at the box it occupied, horizontally scaled so the box it *now* occupies is the same one.
Scaling rather than trusting the font's own advance is what makes the reconstruction exact: the
original page sets a title in bold and a table in regular, and a text layer re-emitted in one face
would place every following word slightly wrong — enough for `source/layout.py`, which measures a
column break as a gap in ems, to read a heading as two columns.

**A space is drawn between two words that were a space apart.** `pdfplumber` splits a run of text
into words on a blank character *or* on a horizontal gap wider than its tolerance, and a text layer
made only of positioned words has no blank characters in it: `Numer faktury:` came back as one word.
The gap glyph is what an OCR engine emits for the same reason.

**The skew is applied to the image and not to the text.** The words are where a perfect OCR with
deskew would put them, which is the same assumption `searchable` already makes about the recognition
itself. A rung that also skewed the text layer would be measuring a second failure — misplaced
boxes — that no reader in this project is equipped to notice.

**Only visible ink is re-emitted, and that is where the idealisation stops.** `searchable` assumes
the recognition is perfect; it does not assume it is clairvoyant. A word printed in white on white
paper contributes no pixel to the image, so no recogniser reading that image can return it, and
copying it forward out of the original text layer would be the one place this rung handed a reader
something the scanner had destroyed. It is not a hypothetical: M6's `invisible` placement is exactly
that word, and the composed corpus in `degrade/attacked.py` measures what a scan does to it. On a
corpus nobody attacked no page carries white ink, which is why this changes not one byte of
`data/scanned` — asserted in `tests/test_degrade_page.py` rather than argued here.
"""

from __future__ import annotations

import io
import random
from dataclasses import dataclass

from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

from doc_extract.degrade import optics
from doc_extract.degrade.rungs import Rung
from doc_extract.source import raster
from doc_extract.source.words import Word, read_words
from doc_extract.synth import render as synth_render
from doc_extract.synth.build import Document

#: PDF text render mode 3: draw nothing, but place the glyphs. What makes a scan searchable.
INVISIBLE = 3

#: How far apart two words' baselines may sit and still count as the same printed line, in points.
#: Only used to decide whether the gap between them deserves a space glyph, so it is a tolerance
#: rather than a layout rule — `source/layout.py` owns the real one.
SAME_LINE_POINTS = 1.0


@dataclass(frozen=True, slots=True)
class Scan:
    """The scanned PDF and its page count — `synth.corpus.Page`, satisfied structurally."""

    data: bytes
    pages: int
    #: The encoded page images that went into it, in page order. Carried rather than recomputed
    #: because `degrade/attacked.py` needs exactly these bytes to ask whether an overlay left a
    #: mark, and rasterising the same page a second time to get them back is the expensive half of
    #: that build. Not part of the `Page` protocol, which wants only `data` and `pages`.
    images: tuple[bytes, ...] = ()


def render(document: Document, rung: Rung) -> Scan:
    """One document, printed by M2 and then scanned at the given rung."""
    printed = synth_render.render(document)
    return scan(printed.data, rung, seed=document.seed)


def scan(data: bytes, rung: Rung, *, seed: int) -> Scan:
    """Any PDF through the scanner. Deterministic in `seed`, and in nothing else."""
    #: The text layer is measured with the same font the page was set in, so the metrics have to be
    #: loaded even when this is called on a PDF this project did not render.
    synth_render.register_fonts()
    sizes = raster.page_sizes(data)
    images = damaged(data, rung, seed=seed)
    words = tuple(word for word in read_words(data) if word.visible) if rung.text_layer else ()

    sink = io.BytesIO()
    canvas = Canvas(sink, pagesize=sizes[0])
    for number, (image, size) in enumerate(zip(images, sizes, strict=True), start=1):
        canvas.setPageSize(size)
        canvas.drawImage(ImageReader(io.BytesIO(image)), 0, 0, width=size[0], height=size[1])
        if rung.text_layer:
            here = [word for word in words if word.page == number]
            _draw_text_layer(canvas, here, height=size[1])
        canvas.showPage()
    canvas.save()
    return Scan(data=sink.getvalue(), pages=len(images), images=images)


def damaged(data: bytes, rung: Rung, *, seed: int) -> tuple[bytes, ...]:
    """What the scanner leaves on the glass: one encoded image per page, before any text is added.

    Separate from `scan` because it is the only thing a *reader looking at the page* ever gets, and
    `degrade/attacked.py` compares two of these to ask whether an overlay left a mark at all.
    Deterministic in `seed` for the same reason `scan` is, and in the same way: two documents that
    share a seed meet the same grain, so a difference between their images is the ink and not the
    sensor.
    """
    rng = random.Random(seed)
    return tuple(
        _degrade(image, rung, rng) for image in raster.pages(data, dpi=rung.dpi)
    )


def _degrade(image: Image.Image, rung: Rung, rng: random.Random) -> bytes:
    """The optics in the order a scanner applies them: geometry, lens, sensor, codec."""
    skewed = optics.skew(image, rung.skew_degrees)
    softened = optics.soften(skewed, rung.blur)
    return optics.requantise(optics.grain(softened, rng, rung.grain), rung.quality)


def _draw_text_layer(canvas: Canvas, words: list[Word], *, height: float) -> None:
    """Every word invisibly at its own box, with a space glyph wherever one was printed."""
    if not words:  # pragma: no cover — every page of this corpus carries words
        return
    text = canvas.beginText()
    text.setTextRenderMode(INVISIBLE)
    for index, word in enumerate(words):
        baseline = height - word.bottom
        _place(text, word.text, size=word.size, left=word.x0, right=word.x1, baseline=baseline)
        following = words[index + 1] if index + 1 < len(words) else None
        if following is None or abs(following.bottom - word.bottom) > SAME_LINE_POINTS:
            continue
        if following.x0 > word.x1:
            _place(text, " ", size=word.size, left=word.x1, right=following.x0, baseline=baseline)
    canvas.drawText(text)


def _place(text, string: str, *, size: float, left: float, right: float, baseline: float) -> None:
    """Draw `string` so that it starts at `left` and ends at `right`, whatever its natural width."""
    natural = pdfmetrics.stringWidth(string, synth_render.REGULAR, size)
    if natural <= 0 or right <= left:  # pragma: no cover — a zero-width word has no box to fill
        return
    text.setFont(synth_render.REGULAR, size)
    text.setHorizScale(100.0 * (right - left) / natural)
    text.setTextOrigin(left, baseline)
    text.textOut(string)
