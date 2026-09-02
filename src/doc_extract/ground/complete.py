"""The page has not finished saying it — a value that stops where the printing does not.

`place.py` answers *where* a text value sits. It cannot answer whether the reading took all of it,
and M7h measured how much that costs: 273 of `pattern`'s 292 wrong values still ground, and the
dominant failure is a description that stops early. The obvious check — did the value claim the
whole cell it sat in? — is blind to almost exactly this population: **161 of the 162** wrong
descriptions that ground claim their *entire* cell. (ADR-0002 recorded that as 100 %; re-measured
here it is one short, and the exception is `multi_page-0010`'s eleventh description, the bare word
`kg`.) The renderer wraps a description across lines and
`source/layout.py` makes each line its own cell, so the reader took one whole cell of a two-cell
run and nothing about that cell is unclaimed.

So the question has to be asked of the page instead of the cell, and ADR-0002 scoped it: **a
completeness check must tell *the rest of my wrapped value* from *the next field down this
column*.** Neither the cell nor the column decides it — asking it of the whole column region fails
the control the other way, because the region also holds the neighbouring field. *(ADR-0002 puts a
figure on that; it is one of the one-off controls `docs/findings.md` warns are not reproducible
from any artifact, the rule it measured does not exist in this code, and a re-derivation here did
not land on it — so it is cited rather than repeated.)* The page decides it, and it decides it
structurally: **in a table, a continuation line carries only the wrapping column while a new row
carries all of them.**

Two bounds make that usable, and each was measured by removing it and counting what the control
then costs — gold values on a reading with nothing wrong in it anywhere:

* **The line below must carry fewer cells than the row does.** Without it the rule asks *is there
  anything below this value in its column, and is the value inside a table row* — and every corpus
  here answers yes too often: **72** gold values on `data/synthetic`, 72 on `data/foreign`, 84 on
  `data/attacked`, 72 and 42 on the two scanned ones, plus 68 of `pattern`'s correct readings.
* **The value's last cell must have something printed to its left on its own line.** This is what
  says the value is in a *table row* rather than at the head of a left-aligned block. It costs
  nothing on four of the five corpora and **72** gold values on `data/foreign`, which is the whole
  reason it is here: the `statement` dialect prints a party as its name beside a right-hand label
  with its address on the line below, so the address is a narrower line under a wider one and
  continues nothing. The mirror-image bound — something to the *right* as well — gives the
  identical control and the identical catch on every corpus here, so it is left out as unmeasured
  strictness rather than kept as insurance. The label on the right is exactly what makes that block
  look like a row, which is why the side is named rather than symmetric.

With **neither** bound the rule is *is there anything below this value in its column*, which fires
on **1169 of `data/synthetic`'s 1238** gold text values — nine in ten of a perfect reading. That
figure belongs to the pair, not to either one, and the two bullets above are what each costs on its
own; conflating the three is how an earlier draft of this docstring credited one bound with the
other's evidence.

**A third bound is not measured the same way, and its cost is real.** `_below` looks only in the
value's own **column**. Dropping that — nearest cell below *anywhere* on the page — costs no gold
false alarm on `data/synthetic` and takes `pattern` from 125 catches to **161**, still with none on
a correct reading. It is kept anyway, and the distinction is the one this package keeps relearning:
the right-flank bound was rejected because it adds a *condition* without changing what the rule
claims, while the column is what the claim **is** — *the page wraps this value one line further down
its column*. Without it those 36 extra values are flagged because something narrower happens to sit
below and to one side, which on a reader as wrong as `pattern` is right by accident. M7h's founding
finding was a value grounding *for a reason that has nothing to do with the field being right*, and
36 catches is not worth reintroducing it one column over.

That the second bound is invisible on four corpora and load-bearing on the fifth is worth stating
plainly: **`data/foreign` earned its keep here as a control**, not as the held-out test it was
built to be.

**What does not discriminate is the gap**, and that is worth recording because it was the first
thing to try. The vertical clearance between the value's last cell and the line beneath it is
**0.30** cell-heights for every one of `pattern`'s 125 truncations and **0.32** for every one of the
72 gold values the flank bound rescues. A wrapped continuation and the next field of a block sit at
the same leading, so no threshold between them exists to be found.

**The direction is downward only, and that too is measured rather than assumed.** The mirror
question — did the reading start *late*, taking a continuation line without the row it wraps from —
gives the identical numbers on every corpus and run here, so it buys nothing this corpus can show;
it is not built, rather than built and silent. `docs/findings.md` carries the sweep.

**What it cannot see is one line further down, and `Frame.continues` carries why.** A reading that
stopped on a *wrap* line rather than on the row is invisible here, because deciding it needs to know
whether the line below belongs to this row or to the next — and on the layout that wraps most, a
complete value's tail is followed by the next row's own head, which looks exactly the same. That is
ADR-0002's ambiguity surviving into the rule that was built to answer it, narrowed to one line.

**This is a signal about a value, not a verdict on it.** It fires on a reading that is grounded —
everything it claims is on the page, in one place — and says the page carried more. That is a
different claim from grounding's and it is kept apart from `Support` for the same reason
`ground/joint.py` is: grounding reports 100 % precision over 24 runs, and folding a second question
into that number would make it a number about two things.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass

from doc_extract.eval.fields import BY_NAME, Match
from doc_extract.ground.place import WRAP_REACH, shares_column
from doc_extract.ground.resolve import Grounding, Support
from doc_extract.source.document import LINE_BREAK, SourceDocument, Span


def cut_short(
    document: SourceDocument, groundings: Iterable[Grounding]
) -> frozenset[tuple[str, str]]:
    """The field instances whose value the page continues past where the reading stopped.

    Keyed `(field, key)` to match `Grounding`, the scorer and `ground/joint.py`, so a caller can
    read this beside a score and a contention without a second naming convention.

    Only `GROUNDED` **text** values are asked about. A value the page does not carry is already
    grounding's to report; and the spans of a non-text value are every occurrence of the winning
    candidate rather than a place, so a rule reading them as a location would be reading the wrong
    thing — `docs/adr/0002_placement.md` carries why that path was left as it is.
    """
    frame = Frame.of(document)
    return frozenset(
        (grounding.field, grounding.key)
        for grounding in groundings
        if _asked(grounding) and frame.continues(frame.cells_of(grounding.spans))
    )


def _asked(grounding: Grounding) -> bool:
    return (
        grounding.support is Support.GROUNDED
        and bool(grounding.spans)
        and BY_NAME[grounding.field].match is Match.TEXT
    )


@dataclass(frozen=True, slots=True)
class Frame:
    """One document's cells, plus the printed line each of them came off.

    A line is what `source/document.assemble` already recorded and no consumer has needed until
    now: cells are joined by a tab and lines by a newline, so two cells are on one line exactly when
    no newline separates them in the text. Read out of the separators rather than re-derived from
    the boxes, because re-deriving it would be a second implementation of `layout.group_lines` —
    two answers to one question, free to drift apart, and this rule's whole content is which line a
    cell is on.
    """

    cells: tuple[Span, ...]
    #: Cell indices per printed line, in reading order.
    lines: tuple[tuple[int, ...], ...]
    #: Which line each cell is on, by cell index.
    line_of: tuple[int, ...]
    #: Every cell's start offset, for `cells_of` to bisect.
    starts: tuple[int, ...]

    @classmethod
    def of(cls, document: SourceDocument) -> Frame:
        lines: list[list[int]] = []
        for index, cell in enumerate(document.cells):
            joined = document.text[document.cells[index - 1].end:cell.start] if index else ""
            if index and LINE_BREAK not in joined:
                lines[-1].append(index)
            else:
                lines.append([index])
        line_of = [0] * len(document.cells)
        for number, line in enumerate(lines):
            for cell in line:
                line_of[cell] = number
        return cls(
            cells=document.cells,
            lines=tuple(tuple(line) for line in lines),
            line_of=tuple(line_of),
            starts=tuple(cell.start for cell in document.cells),
        )

    def cells_of(self, spans: Iterable[Span]) -> frozenset[int]:
        """The cells a place's word spans fall inside. A word sits in exactly one cell.

        Found by bisecting the starts rather than by scanning: `source/document.assemble` writes
        cells in reading order and never overlapping, so the cell holding an offset is the last one
        that begins at or before it. A document has a few hundred cells and a reading has sixty
        values with several spans each, and the scan this replaced was the whole cost of the rule.
        """
        found: set[int] = set()
        for span in spans:
            index = bisect_right(self.starts, span.start) - 1
            if index >= 0 and span.end <= self.cells[index].end:
                found.add(index)
        return frozenset(found)

    def continues(self, claimed: frozenset[int]) -> bool:
        """Whether the page wraps this value one line further than the reading took it.

        **Both questions are asked of the value's last cell, and that is the bound on what this
        rule can see.** A reading that already ran past the row and stopped on a wrap line has
        nothing printed to its left — a wrap line carries one column by definition — so it is not
        flanked and the rule stays silent. It sees a truncation that stopped **on the row**, and no
        other kind.

        That is a limit and it was chosen against the alternative rather than settled for. Asking
        the flank of the value's *row* instead — the widest line the value sits on — would see the
        other kind too, and it fails the control on every corpus here: **133** gold values on
        `data/synthetic`, 42 on `data/foreign`, 105 on `data/attacked`, 70 and 63 on the two
        scanned ones. The mechanism is the ambiguity ADR-0002 named, in its sharpest form: the
        `classic` layout centres a description on its row, so a three-line one prints head, row,
        tail — and a **complete** value's tail is followed by the *next row's head*, which is a
        narrower line in the same column and structurally identical to a continuation. Bounding
        that variant to the wrap line adjacent to the row restores the control and catches **not
        one** wrong value more than this rule does, on any of the 29 corpora and runs measured. So
        the wider question is not merely dangerous, it is unrewarded here, and what is left open is
        stated rather than approximated.
        """
        if not claimed:
            return False
        #: Reading order breaks a tie, so the answer is a property of the page rather than of the
        #: order a `frozenset` happened to iterate in. A place holds one column, so two of its cells
        #: cannot share a line and the tie should not arise — which is the reason to spend a
        #: tie-break on it rather than to leave it to chance.
        last = max(claimed, key=lambda index: (self.cells[index].bottom, -index))
        if not self._flanked(last):
            return False
        below = self._below(last)
        return below is not None and len(self.lines[self.line_of[below]]) < len(
            self.lines[self.line_of[last]]
        )

    def _flanked(self, cell: int) -> bool:
        """Whether this cell's own line prints something to its left — i.e. it is in a table row.

        The left is the side that decides, because the shape being excluded is a **left-aligned
        block**: a party's address under its name begins where the name begins, and a narrower line
        under a wider one there is the next field rather than a wrap. A right-hand label does not
        make a block a table, which is why asking about the right would not have excluded it.
        """
        here = self.cells[cell]
        return any(
            self.cells[other].x1 <= here.x0 for other in self.lines[self.line_of[cell]]
            if other != cell
        )

    def _below(self, cell: int) -> int | None:
        """The nearest cell beneath this one in its column, within a wrap's reach.

        The same column test and the same reach `place.Sheet` uses to assemble a place, because the
        question is *did the place stop one line early* and a rule looking further than a place can
        extend would be asking about a line no place could have held.

        **Its answer cannot be a cell the value already claimed**, so there is no guard for that and
        the absence is deliberate: the caller passes the *bottom-most* claimed cell, and anything
        this returns starts at or below that cell's baseline and therefore ends below it.
        """
        here = self.cells[cell]
        height = here.bottom - here.top or 1.0
        nearest: tuple[float, int] | None = None
        for index, other in enumerate(self.cells):
            if index == cell or other.page != here.page or not shares_column(other, here):
                continue
            gap = other.top - here.bottom
            if 0.0 <= gap <= WRAP_REACH * height and (nearest is None or gap < nearest[0]):
                nearest = (gap, index)
        return None if nearest is None else nearest[1]
