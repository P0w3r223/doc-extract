"""Lines and cells, recovered from geometry — the step a flat text dump cannot do.

Two groupings happen here, and each answers a question the printed page answers unambiguously and a
string does not.

**Which words share a line?** Vertical overlap, not equal `top`. A table row sets `Lp.` at 8 pt and
its description at 7.5 pt, so the two boxes start at different heights while plainly belonging to
the same row. Overlap of more than half the shorter box is the test; equality of `top` would split
that row in two.

**Which words share a cell?** The horizontal gap, measured against the font size rather than in
absolute points, because a wide gap at 7.5 pt is a narrow one at 12 pt. The two populations this
has to separate are far apart and both bounded:

* Inside a value, the gap is one space — 0.32 em in DejaVu, so 2.5 pt at 8 pt type. This is the gap
  in `1 234,56`, whose thousands separator `pdfplumber` treats as a word break.
* Between two columns, the gap is at least 12 pt. Not by assumption:
  `tests/test_synth_render.py::test_no_cell_in_the_corpus_overruns_its_column` requires every cell's
  text to fit its column with reportlab's 6 pt of padding on each side still to spare, and that
  slack *is* the gap between one right-aligned value and the next.

`COLUMN_GAP_EM` sits between them with room on both sides. A cell is therefore what the page shows
as one field, and `3` beside `466,62` stays two fields — which is the whole point of reading
geometry instead of a string.
"""

from __future__ import annotations

from dataclasses import dataclass

from doc_extract.source.words import Word

#: A horizontal gap wider than this many em starts a new cell. A space is 0.32 em and a column gap
#: is at least 1.5 em (see the module docstring), so the threshold is not finely tuned — it is the
#: middle of an order-of-magnitude gap between the two things it separates.
COLUMN_GAP_EM = 0.75

#: Fraction of the shorter box two words must overlap vertically to count as one line.
LINE_OVERLAP = 0.5


@dataclass(frozen=True, slots=True)
class Cell:
    """One field of the page: the words that a reader would see as a single value."""

    words: tuple[Word, ...]

    @property
    def text(self) -> str:
        """The words joined by single spaces — the form the page prints them in."""
        return " ".join(word.text for word in self.words)

    @property
    def x0(self) -> float:
        return min(word.x0 for word in self.words)

    @property
    def x1(self) -> float:
        return max(word.x1 for word in self.words)

    @property
    def top(self) -> float:
        return min(word.top for word in self.words)

    @property
    def bottom(self) -> float:
        return max(word.bottom for word in self.words)


@dataclass(frozen=True, slots=True)
class Line:
    """One printed line of one page, split into the fields it carries."""

    page: int
    cells: tuple[Cell, ...]


def group_lines(words: tuple[Word, ...]) -> tuple[Line, ...]:
    """Words grouped into lines by vertical overlap, then into cells by horizontal gap.

    Lines come out ordered down the page, pages in order, and cells left to right — which is the
    order a reader takes them in, and the order the text layer is assembled in.
    """
    lines: list[Line] = []
    for page in sorted({word.page for word in words}):
        on_page = sorted(
            (word for word in words if word.page == page), key=lambda word: (word.top, word.x0)
        )
        for row in _rows(on_page):
            lines.append(Line(page=page, cells=split_cells(row)))
    return tuple(lines)


def _rows(words: list[Word]) -> list[list[Word]]:
    """Consecutive words gathered while they still overlap the row being built."""
    rows: list[list[Word]] = []
    top = bottom = 0.0
    for word in words:
        if rows and _overlaps(top, bottom, word):
            rows[-1].append(word)
            top, bottom = min(top, word.top), max(bottom, word.bottom)
            continue
        rows.append([word])
        top, bottom = word.top, word.bottom
    return rows


def _overlaps(top: float, bottom: float, word: Word) -> bool:
    shared = min(bottom, word.bottom) - max(top, word.top)
    shorter = min(bottom - top, word.bottom - word.top)
    return shorter > 0 and shared > LINE_OVERLAP * shorter


def split_cells(row: list[Word]) -> tuple[Cell, ...]:
    """One row of words, cut wherever the gap is too wide to be a space."""
    ordered = sorted(row, key=lambda word: word.x0)
    cells: list[list[Word]] = []
    for word in ordered:
        if cells and word.x0 - cells[-1][-1].x1 <= _threshold(cells[-1][-1], word):
            cells[-1].append(word)
        else:
            cells.append([word])
    return tuple(Cell(words=tuple(cell)) for cell in cells)


def _threshold(left: Word, right: Word) -> float:
    """Measured against the larger of the two sizes, so a small word beside a heading survives."""
    return COLUMN_GAP_EM * max(left.size, right.size)
