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

**A word also carries whether it was printed in ink that leaves a mark.** Nothing in the extraction
path cares — `source/document.py` reads a text layer, and a text layer does not have a colour — but
`degrade/page.py` does, because the `searchable` rung re-emits the words an OCR engine would have
recovered and an OCR engine recovers what is *on the image*. M6's `invisible` placement prints its
payload in white, so a rung that copied every word forward would carry an attack across a scan that
physically erased it. The test is deliberately narrow: **white fill on white paper**, which is the
one way this project's renderer hides text, and not a general solver for what a human can see. A
word whose colour the PDF does not state is called visible, because between overstating and
understating what an attacker gets onto a page, the honest direction is the one that does not
flatter the defence.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

import pdfplumber

#: Font size assumed when the PDF does not state one. Every document this project renders states it;
#: the fallback exists so a real-world scan with an odd text layer degrades instead of raising.
DEFAULT_SIZE = 10.0

#: How close to the paper a fill has to be before the word it draws is called invisible. White ink
#: is exactly 1.0 in this project's renderer; the margin is for a PDF that writes it as 0.999.
WHITE_LEVEL = 0.98


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
    #: Whether the ink leaves a mark. `True` for every ordinary word, and for every word whose
    #: colour the PDF does not state — see the module docstring for which direction that errs in.
    visible: bool = True


def read_words(data: bytes) -> tuple[Word, ...]:
    """Every word of every page, in the order `pdfplumber` reports them.

    That order is roughly top-to-bottom, left-to-right, and it is deliberately *not* relied on:
    `layout` re-derives lines from the boxes. Reading order is an interpretation of geometry, and
    the interpretation belongs where it can be tested.

    Asking for the fill colour is also asking `pdfplumber` to end a word wherever the colour
    changes. That is a split this project wants rather than tolerates — a run of text that is half
    white is half hidden, and a single word carrying one visibility for both halves would have to
    lie about one of them — and `tests/test_source_words.py` holds it to changing nothing on a
    corpus where no such run exists.
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
                visible=not _is_white(word.get("non_stroking_color")),
            )
            for number, page in enumerate(pdf.pages, start=1)
            for word in page.extract_words(extra_attrs=["size", "non_stroking_color"])
        )


def _is_white(colour: Any) -> bool:
    """Whether a fill is the paper's own white, in the colour spaces a PDF states one in.

    Grey and RGB say white by being at the top of their range; CMYK says it by carrying no ink at
    all. Anything else — a named space, a pattern, a missing value — is not something this function
    claims to understand, and it answers `False` so that the word stays visible.
    """
    if not isinstance(colour, (tuple, list)) or not colour:
        return False
    try:
        levels = [float(component) for component in colour]
    except (TypeError, ValueError):  # pragma: no cover — a pattern name rather than a number
        return False
    if len(levels) in (1, 3):
        return all(level >= WHITE_LEVEL for level in levels)
    if len(levels) == 4:
        return all(level <= 1.0 - WHITE_LEVEL for level in levels)
    return False  # pragma: no cover — no colour space this project renders has another arity
