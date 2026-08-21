"""A text value has to be found in one place, and these are the ways the old tally was not.

`resolve` used to ask of each word separately whether it was anywhere on the page. Every test here
would have passed under that reading except the ones that matter, and the first is the failure that
was found on the real corpus rather than imagined: `clean-0001` grounded the buyer's `sp. z o.o.`
against the **seller's** legal form at the top of the page, and reported the buyer's name fully
supported on evidence belonging to another company.

The corpus-scale control lives in `test_ground.py` — gold must ground completely against its own
page — and it is the reason `WRAP_REACH` exists at all. These are the small cases that say *why*
each part of a place is shaped the way it is, on pages laid out by hand so the geometry is the
thing under test rather than a property of `synth/render.py`.
"""

from __future__ import annotations

import pytest

from doc_extract.eval.fields import SINGLETON
from doc_extract.ground.place import Sheet, bare
from doc_extract.ground.resolve import Support, resolve
from doc_extract.source import document as source_document
from doc_extract.source.layout import Cell, Line
from doc_extract.source.words import Word

#: Nominal type size, and a character width at that size. Both only have to be self-consistent:
#: `WRAP_REACH` is measured in multiples of a cell's own height, so a page built here is judged by
#: the same rule as a rendered one.
SIZE = 8.0
CHAR = 5.0
LINE_HEIGHT = 10.0


def _cell(words: list[str], *, x: float, top: float) -> Cell:
    """One cell of one row, starting at `x`, its words a space apart."""
    made = []
    for text in words:
        width = len(text) * CHAR
        made.append(Word(text=text, x0=x, x1=x + width, top=top, bottom=top + SIZE,
                         page=1, size=SIZE))
        x += width + CHAR
    return Cell(words=tuple(made))


def _page(*rows: list[tuple[float, list[str]]]):
    """A document from cells at explicit horizontal positions.

    `test_ground.py`'s builder lays cells out left to right automatically, which cannot express two
    blocks side by side — and a value grounding against the block on the *other* side of the page
    is the whole subject here. So this one takes the `x` of every cell.
    """
    return source_document.assemble(tuple(
        Line(page=1, cells=tuple(_cell(words, x=x, top=index * LINE_HEIGHT)
                                 for x, words in cells))
        for index, cells in enumerate(rows)
    ))


def _described(invoice, description: str):
    """The invoice with one line item carrying `description` — the text field with most words."""
    return invoice.model_copy(update={
        "lines": (invoice.lines[0].model_copy(update={"description": description}),),
    })


def _ground(page, invoice, field="lines[].description", key="1"):
    return {(g.field, g.key): g for g in resolve(page, invoice)}[(field, key)]


# --------------------------------------------------------------------------- the regression


def test_a_value_does_not_ground_on_another_fields_words_across_the_page(invoice):
    """The failure this module was written for, in the shape the corpus produced it.

    Two parties are printed side by side. The buyer's name needs `sp. z o.o.` and only the seller
    prints it. Under a page-wide tally the buyer grounded **completely**, on the seller's ink.

    The coverage is 3/5 rather than 2/5, and that is worth asserting rather than rounding off: the
    place holding most of this value is the *seller's* cell, which prints three of its five words
    — `sp`, `z`, `o.o` — against the buyer cell's two. Anchors are ranked by how many wanted words
    a cell holds and nothing weights a distinctive word above a common one, because any such
    weighting would be fitted to the names this corpus happens to print. What the constraint buys
    is not the right place every time; it is that no place holds all five, so the value stops
    being reported as fully supported.
    """
    page = _page(
        [(50.0, ["Acme", "sp.", "z", "o.o."]), (300.0, ["Przychodnia", "VITAMED"])],
    )
    one = invoice.model_copy(update={
        "buyer": invoice.buyer.model_copy(update={"name": "Przychodnia VITAMED sp. z o.o."}),
    })
    grounded = _ground(page, one, field="buyer.name", key=SINGLETON)

    assert grounded.support is Support.PARTIAL
    assert grounded.coverage == pytest.approx(3 / 5)
    assert grounded.suspicious


def test_the_same_name_printed_whole_in_one_place_still_grounds(invoice):
    """The positive control for the test above: the constraint is *one place*, not *fewer words*."""
    page = _page(
        [(50.0, ["Acme", "sp.", "z", "o.o."]),
         (300.0, ["Przychodnia", "VITAMED", "sp.", "z", "o.o."])],
    )
    one = invoice.model_copy(update={
        "buyer": invoice.buyer.model_copy(update={"name": "Przychodnia VITAMED sp. z o.o."}),
    })
    assert _ground(page, one, field="buyer.name", key=SINGLETON).support is Support.GROUNDED


def test_the_spans_that_come_back_are_one_place_and_not_every_occurrence(invoice):
    """What makes the spans a location: they must be the place chosen, not each word's first hit."""
    page = _page(
        [(50.0, ["Usługa", "porządkowa"])],
        [(300.0, ["Usługa", "kurierska"])],
    )
    grounded = _ground(page, _described(invoice, "Usługa kurierska"))

    assert grounded.support is Support.GROUNDED
    assert {round(span.x0) for span in grounded.spans} == {300, 335}, (
        "the second row is where this value is; the first only shares a word with it"
    )


# --------------------------------------------------------------------------- what a place is


def test_a_value_wrapped_into_the_next_row_of_its_own_column_grounds(invoice):
    """A long description is broken across lines and each line becomes its own cell.

    Without this the anchor cell would hold half the value, which is 52.1 % of gold — the
    measurement that put `WRAP_REACH` in the module rather than leaving a place at one cell.
    """
    page = _page(
        [(50.0, ["Wynajem", "powierzchni"]), (300.0, ["1", "szt."])],
        [(50.0, ["magazynowej"])],
    )
    assert _ground(page, _described(invoice, "Wynajem powierzchni magazynowej")).support \
        is Support.GROUNDED


def test_a_word_taken_from_the_next_column_does_not_count(invoice):
    """`pattern`'s failure: a description stitched from its own cell and the unit beside it.

    The column is the bound that does the work here — removing it takes the catch on that
    baseline from 19 wrong descriptions to none.
    """
    page = _page(
        [(50.0, ["Hosting", "serwera"]), (300.0, ["mies."])],
    )
    grounded = _ground(page, _described(invoice, "Hosting serwera mies."))

    assert grounded.support is Support.PARTIAL
    assert grounded.coverage == pytest.approx(2 / 3)


def test_a_row_far_down_the_same_column_is_out_of_reach(invoice):
    """A column is not a place. `WRAP_REACH` bounds a continuation to a neighbouring row."""
    page = _page(
        [(50.0, ["Wynajem", "powierzchni"])],
        *[[(50.0, ["wypełniacz"])] for _ in range(6)],
        [(50.0, ["magazynowej"])],
    )
    assert _ground(page, _described(invoice, "Wynajem powierzchni magazynowej")).support \
        is Support.PARTIAL


def test_a_word_claimed_twice_needs_one_place_to_print_it_twice(invoice):
    """Multiplicity is counted per place, which is what makes it a claim about a location.

    Page-wide, `Usługa` appears twice and a value asking for it twice was satisfied. The two
    occurrences are in different columns, so no single place holds both.
    """
    page = _page(
        [(50.0, ["Usługa"]), (300.0, ["Usługa"])],
    )
    grounded = _ground(page, _described(invoice, "Usługa Usługa"))

    assert grounded.support is Support.PARTIAL
    assert grounded.coverage == 0.5


def test_the_place_holding_most_of_the_value_wins(invoice):
    """The anchor is chosen by how much of the value it holds, not by where it sits on the page."""
    page = _page(
        [(50.0, ["Audyt"])],
        [(50.0, ["Audyt", "bezpieczeństwa", "sieci"])],
    )
    grounded = _ground(page, _described(invoice, "Audyt bezpieczeństwa sieci"))

    assert grounded.support is Support.GROUNDED
    assert {round(span.top) for span in grounded.spans} == {10}


# --------------------------------------------------------------------------- the shared normaliser


def test_both_sides_of_a_comparison_are_bared_by_one_function():
    """A page bared differently from a value would fail to match for a reason nobody could see.

    `resolve` bares the value's tokens and `place` bares the page's words, and both call this.
    Asserting the identity rather than the behaviour is what stops the two drifting apart — the
    same discipline `test_ground.py` applies to the amount projection, one layer up.
    """
    from doc_extract.ground.resolve import bare as bares_the_value

    assert bares_the_value is bare
    assert bare("Rynek,") == bare("Rynek") == "Rynek"


def test_a_word_that_is_only_punctuation_is_not_a_place_to_look_for(invoice):
    """The renderer draws an en dash inside a description as its own word.

    It carries nothing to find, so it is dropped from both the value and the page — otherwise
    every such description would lose coverage for a character no reading could get wrong.

    The dash is written as a code point for the reason `place._EDGE_PUNCTUATION` is: an en dash and
    a hyphen are hard to tell apart in a diff, and which one this is decides what the test proves.
    """
    dash = chr(0x2013)
    page = _page([(50.0, ["Hosting", dash, "abonament"])])
    grounded = _ground(page, _described(invoice, f"Hosting {dash} abonament"))

    assert grounded.support is Support.GROUNDED
    assert grounded.coverage == 1.0


def test_an_empty_value_is_not_a_question_about_a_place():
    """`Sheet.locate` is total: asked for nothing, it answers that nothing was missing."""
    sheet = Sheet(_page([(50.0, ["Cokolwiek"])]))
    located = sheet.locate(())

    assert located.coverage == 1.0
    assert located.spans == ()
