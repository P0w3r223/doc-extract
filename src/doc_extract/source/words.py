"""Words as the PDF places them: text plus the box it occupies, before any reading order is imposed.

`pdfplumber.extract_text()` returns a page as a single string, and that string has already thrown
away the one thing this project needs. A quantity of `3` printed beside a price of `466,62` comes
back as `3 466,62`, because a space is also Poland's thousands separator — the column boundary that
distinguished them was geometry, and a flat dump does not carry geometry.

So the unit here is a word with its box. `x0`/`x1` are the horizontal extent in points, `top` and
`bottom` the vertical one measured from the top of the page, and `size` is the font size the word
was set in — which `layout` needs, because "a wide gap" is only meaningful relative to how wide a
space is at that size.

Word splitting is `pdfplumber`'s: a blank character ends a word, so the `1` and the `234,56` of a
printed `1 234,56` arrive as two words. Rejoining them is `layout`'s job and it is not guesswork —
they sit a space apart, while two columns sit twelve points apart at the very least.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import pdfplumber

#: Font size assumed when the PDF does not state one. Every document this project renders states it;
#: the fallback exists so a real-world scan with an odd text layer degrades instead of raising.
DEFAULT_SIZE = 10.0


@dataclass(frozen=True, slots=True)
class Word:
    """One word of the text layer, and where on which page it was drawn."""

    text: str
    page: int          #: 1-based, as a reader would count them
    x0: float
    x1: float
    top: float
    bottom: float
    size: float


def read_words(data: bytes) -> tuple[Word, ...]:
    """Every word of every page, in the order `pdfplumber` reports them.

    That order is roughly top-to-bottom, left-to-right, and it is deliberately *not* relied on:
    `layout` re-derives lines from the boxes. Reading order is an interpretation of geometry, and
    the interpretation belongs where it can be tested.
    """
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return tuple(
            Word(
                text=word["text"],
                page=number,
                x0=float(word["x0"]),
                x1=float(word["x1"]),
                top=float(word["top"]),
                bottom=float(word["bottom"]),
                size=float(word.get("size", DEFAULT_SIZE)),
            )
            for number, page in enumerate(pdf.pages, start=1)
            for word in page.extract_words(extra_attrs=["size"])
        )
