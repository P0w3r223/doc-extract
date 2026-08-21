"""Where on the page a value sits — as opposed to whether its parts are somewhere on it.

`resolve` used to answer a text field by tallying: for each word of the value, is that word anywhere
on this page? It is a fair question about *existence* and it was never a question about *location*,
and the difference is not academic. `clean-0001` prints the buyer as `Przychodnia Rodzinna VITAMED
sp. z o.o.` in one cell; the tally grounded `Przychodnia`, `Rodzinna` and `VITAMED` against that
cell and then grounded `sp.`, `z` and `o.o.` against the **seller's** legal form at the top of the
page, because that is where those three words occur first. The value was fully grounded and half of
its evidence belonged to a different company. That is the same failure the module docstring of
`resolve` already warns about for exemption codes — *grounding for a reason that has nothing to do
with the field being right* — and it was general rather than confined to rates.

So a text value is **located** here instead: it must be found in one place on the page, and the
spans that come back are that place. Two consequences, and the second is why this module exists at
all rather than being three lines inside `resolve`:

* A value assembled out of two different fields no longer grounds. On M4's `pattern` baseline —
  a regex reader that lifts real text out of the wrong column — 19 of 181 wrong descriptions stop
  being fully grounded, and **not one correct value on any of four populations is lost**.
* The recorded spans become a claim a later check can interrogate. They were not before: a value
  ground to a bag of occurrences cannot be asked whether it sits where the page would print it,
  which is the check M5 named as the complement to the arithmetic. What that check still needs, and
  what measurement says it cannot be, is in `docs/adr/0002_placement.md`.

**A place is a cell, plus where a wrapped value continues.** Not the cell alone: the renderer breaks
a long description across lines and `source/layout.py` makes each line its own cell, so 52.1 % of
*gold* text values do not fit in one — the control that decided this, and the reason `WRAP_REACH`
exists rather than being assumed away. The continuation is looked for in the same column and on a
neighbouring row, which is where a wrapped line goes on any invoice and not only on this one's.

**Of the two bounds, the column is the one that discriminates.** Measured by removing each: without
the column the catch on `pattern` falls from 19 to **0**, while the vertical reach accounts for 1 of
the 19 and every setting from 0.5 upward — to twenty times `WRAP_REACH`, where the region is the
whole column — gives the same control and the same catch. So the reach is not a tuned threshold
sitting between two populations; its job is to *admit* the wrapped continuation, and below 0.5 it
stops doing that and the control breaks. Saying so is the difference between a constant that was
measured and one that was picked.

**The region is therefore deliberately generous, and that direction is chosen.** A different field
one row down in the same column is inside it, so this module can still ground a value against a
neighbour it shares words with — it can no longer ground one against the other side of the page.
Erring toward grounding is the direction that does not manufacture false alarms, and grounding's
precision is the number this project reports.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from doc_extract.source.document import SourceDocument, Span

#: How far a wrapped continuation may sit from the cell it continues, in multiples of that cell's
#: own height. A continuation is the next printed line, so one line-height is the shape of the
#: bound; the slack is for the leading between rows of a table. It is not a threshold that
#: separates two populations — a different field one row down is inside it as well — and the
#: module docstring says which way that errs.
WRAP_REACH = 1.5


@dataclass(frozen=True, slots=True)
class Place:
    """The best single place on the page a value was found, and how much of it was there."""

    spans: tuple[Span, ...]
    #: Matched tokens over wanted tokens, at this place. `1.0` means the whole value is here.
    coverage: float


class Sheet:
    """One document, indexed by cell, so a value can be looked for at a place rather than at large.

    Built once per document and asked once per text field, which is why the token index and the
    per-cell word lists are computed here: locating sixty values by rescanning every word sixty
    times is the shape this replaced.
    """

    __slots__ = ("_by_token", "_cells", "_regions", "_words")

    def __init__(self, document: SourceDocument) -> None:
        self._cells: tuple[Span, ...] = document.cells
        self._words: tuple[tuple[tuple[str, Span], ...], ...] = _words_by_cell(document)
        self._by_token: dict[str, set[int]] = {}
        for index, cell in enumerate(self._words):
            for token, _ in cell:
                self._by_token.setdefault(token, set()).add(index)
        self._regions: dict[int, tuple[int, ...]] = {}

    def locate(self, wanted: tuple[str, ...]) -> Place:
        """The place holding most of `wanted`, and the spans of the words found there.

        `wanted` is already bared of edge punctuation by the caller, and counted with multiplicity:
        a value claiming a word twice needs it twice **in one place**, or one of the two is
        unaccounted for.

        **Anchors are tried by how much of the value the cell holds on its own**, before the region
        extends it. Two places can both reach full coverage — a wrapped value's first line and its
        second line each anchor a region containing the other — and the search stops at the first
        that does, so the order decides which one is reported as the location. Trying the fuller
        cell first makes that the line the value actually sits on rather than whichever came
        earlier down the page. Ties break on reading order, so a run stays reproducible.
        """
        if not wanted:
            return Place((), 1.0)
        want = Counter(wanted)
        best = Place((), 0.0)
        for anchor in self._anchors(want):
            found = self._take(anchor, want)
            if found.coverage > best.coverage:
                best = found
            if best.coverage >= 1.0:
                break
        return best

    def _anchors(self, want: Counter[str]) -> list[int]:
        """Cells holding any of the wanted words, fullest first, then in reading order."""
        candidates = {index for token in want for index in self._by_token.get(token, ())}
        return sorted(candidates, key=lambda index: (-self._held(index, want), index))

    def _held(self, index: int, want: Counter[str]) -> int:
        """How many of the wanted words this one cell holds, counted with multiplicity."""
        taken: Counter[str] = Counter()
        for token, _ in self._words[index]:
            if taken[token] < want[token]:
                taken[token] += 1
        return sum(taken.values())

    def _take(self, anchor: int, want: Counter[str]) -> Place:
        """As much of `want` as the region around `anchor` holds, each occurrence used once."""
        taken: Counter[str] = Counter()
        spans: list[Span] = []
        for index in self._region(anchor):
            for token, span in self._words[index]:
                if taken[token] < want[token]:
                    taken[token] += 1
                    spans.append(span)
        return Place(tuple(spans), sum(taken.values()) / sum(want.values()))

    def _region(self, anchor: int) -> tuple[int, ...]:
        """The anchor cell first, then the cells a wrapped value could continue into.

        Same page, overlapping horizontally — which is what makes them one column, derived from the
        boxes rather than from any knowledge of what the column holds — and within `WRAP_REACH` of
        the anchor vertically, above or below: a value's first line is not always the anchor, since
        the anchor is whichever cell holds most of it.

        **The anchor comes first, and the order is load-bearing.** `_take` uses each occurrence
        once, so whichever cell it reads first gets to claim a shared word. Reading the region in
        page order let a continuation *above* the anchor claim a word the anchor also printed, and
        the spans then pointed at a row the value was not on — the exact confusion this module
        exists to remove, reintroduced two cells away instead of a page away.
        """
        if anchor not in self._regions:
            here = self._cells[anchor]
            height = here.bottom - here.top or 1.0
            self._regions[anchor] = (anchor, *(
                index
                for index, cell in enumerate(self._cells)
                if index != anchor and cell.page == here.page and _shares_column(cell, here)
                and _row_gap(cell, here) <= WRAP_REACH * height
            ))
        return self._regions[anchor]


def _shares_column(cell: Span, anchor: Span) -> bool:
    return min(cell.x1, anchor.x1) > max(cell.x0, anchor.x0)


def _row_gap(cell: Span, anchor: Span) -> float:
    """Vertical clearance between two boxes; zero or less when they overlap, so a row-mate is 0."""
    return max(cell.top - anchor.bottom, anchor.top - cell.bottom, 0.0)


def _words_by_cell(document: SourceDocument) -> tuple[tuple[tuple[str, Span], ...], ...]:
    """Each cell's words, bared, in reading order.

    Both sequences arrive sorted and non-overlapping from `source/document.assemble`, so one walk
    places every word. A word whose bared form is empty — the en dash the renderer draws inside a
    description as its own word — is dropped here for the reason `resolve` drops it from a value:
    it carries nothing to look for, and counting it would dock a place for punctuation.
    """
    cells: list[list[tuple[str, Span]]] = [[] for _ in document.cells]
    at = 0
    for word in document.words:
        while at < len(document.cells) and document.cells[at].end < word.end:
            at += 1
        if at >= len(document.cells):
            break
        if document.cells[at].start <= word.start:
            token = bare(document.text_of(word))
            if token:
                cells[at].append((token, word))
    return tuple(tuple(cell) for cell in cells)


#: Punctuation a line-join or a sentence puts around a word. The last three are written as code
#: points because an ellipsis and the two dashes are hard to tell apart from a hyphen in a diff, and
#: the difference decides whether a description's dash is stripped or looked for on the page.
_EDGE_PUNCTUATION = ".,;:()[]\"'" + "".join(map(chr, (0x2026, 0x2013, 0x2014)))


def bare(token: str) -> str:
    """A word without the punctuation a line-join or a sentence put around it.

    The gold joins an address's lines with a comma, so its second token is `4,` while the page drew
    `4`. Stripping the edges makes the two the same word, and keeps `50-106` and `m²` intact, which
    a blanket alphanumeric filter would not.

    It lives here rather than in `resolve` because both sides of a comparison have to be bared the
    same way, and the page's side is built here.
    """
    return token.strip(_EDGE_PUNCTUATION)
