"""The document as one string, plus the map from every character of it back onto the page.

The string is what a model reads. The map is what M5 needs and cannot reconstruct afterwards: a
grounding check asks "which part of the page does this value come from", and that question is only
answerable if the answer was recorded while the string was being built.

**The separators are chosen so that no character of the document is ambiguous.** Cells are joined by
a tab, lines by a newline, pages by a blank line — three characters that no Polish invoice prints
inside a value, whereas the space is a thousands separator and cannot be used to mean "next field".
`3\t466,62` is a quantity and a price; `1 234,56` is one amount. That distinction is the reason this
layer exists.

**An empty cell leaves no trace.** A row whose discount column is blank comes back with one field
fewer than its neighbours, so the position of a field within a line is not an index into the table's
columns. That is a property of the page rather than of this layer — the column is empty on the page
too, and a reader uses the headers and the values to tell which is which. It is also why the metric
rules say to match by field type and never by position.

**Nothing is added that the document does not contain.** No page markers, no headings, no field
labels. Injected text inside the document could imitate any marker this layer invented, and a
reader with no way to tell our text from the page's text is exactly the confusion the envelope
exists to prevent. Pages announce themselves anyway: every rendered page prints `Strona 1 z 2`.

The invariant that makes the offsets trustworthy is small enough to test directly, and
`tests/test_source_document.py` does: for every span, `text[span.start:span.end]` is that word's or
that cell's own text.
"""

from __future__ import annotations

from dataclasses import dataclass

from doc_extract.source.layout import Cell, Line, group_lines
from doc_extract.source.words import Word, read_words

WORD_BREAK = " "
CELL_BREAK = "\t"
LINE_BREAK = "\n"
PAGE_BREAK = "\n\n"


@dataclass(frozen=True, slots=True)
class Span:
    """A stretch of the document text, and the box on the page it was read from."""

    start: int
    end: int
    page: int
    x0: float
    x1: float
    top: float
    bottom: float


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """One PDF, read back: the text, and where each piece of it sits.

    `words` and `cells` describe the same characters at two granularities. A word is what the PDF
    drew; a cell is what a reader would call one field. Grounding a value like `1 234,56` needs the
    cell, because the word map has it as two pieces; grounding a single digit needs the word.
    """

    text: str
    words: tuple[Span, ...]
    cells: tuple[Span, ...]
    pages: int

    def text_of(self, span: Span) -> str:
        """The characters a span covers. Equal to the word's or cell's own text, by construction."""
        return self.text[span.start:span.end]


def read(data: bytes) -> SourceDocument:
    """A PDF's bytes to a source document. No model, no network, no interpretation."""
    words = read_words(data)
    return assemble(group_lines(words))


def assemble(lines: tuple[Line, ...]) -> SourceDocument:
    """Lay the lines out as text, recording where each word and each cell landed in it."""
    pieces: list[str] = []
    word_spans: list[Span] = []
    cell_spans: list[Span] = []
    cursor = 0
    previous_page: int | None = None

    for line in lines:
        if previous_page is not None:
            separator = PAGE_BREAK if line.page != previous_page else LINE_BREAK
            pieces.append(separator)
            cursor += len(separator)
        previous_page = line.page

        for index, cell in enumerate(line.cells):
            if index:
                pieces.append(CELL_BREAK)
                cursor += len(CELL_BREAK)
            start = cursor
            for position, word in enumerate(cell.words):
                if position:
                    pieces.append(WORD_BREAK)
                    cursor += len(WORD_BREAK)
                pieces.append(word.text)
                word_spans.append(_word_span(word, start=cursor))
                cursor += len(word.text)
            cell_spans.append(_cell_span(cell, page=line.page, start=start, end=cursor))

    return SourceDocument(
        text="".join(pieces),
        words=tuple(word_spans),
        cells=tuple(cell_spans),
        pages=max((line.page for line in lines), default=0),
    )


def _word_span(word: Word, *, start: int) -> Span:
    return Span(
        start=start, end=start + len(word.text), page=word.page,
        x0=word.x0, x1=word.x1, top=word.top, bottom=word.bottom,
    )


def _cell_span(cell: Cell, *, page: int, start: int, end: int) -> Span:
    return Span(
        start=start, end=end, page=page,
        x0=cell.x0, x1=cell.x1, top=cell.top, bottom=cell.bottom,
    )
