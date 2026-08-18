"""What the source layer has to be right about, on the documents the corpus actually renders.

M2's render test could only claim that every gold value is *somewhere* in the text layer, and said
so plainly: finding `466,62` in a flat dump does not mean it can be parsed out, because a quantity
of `3` printed beside it reads as `3 466,62` and a space is Poland's thousands separator. This file
is where that claim gets stronger. Reading geometry, the two are separate cells and the amount with
a thousands space is one cell — which is the difference between a text layer an extractor can be
scored on and one where the corpus itself is the source of the errors.

The offsets are tested just as hard, because M5's grounding depends on them and a wrong offset is
silent: it produces a span that points at the wrong part of a page nobody re-reads.
"""

from __future__ import annotations

import re
from decimal import Decimal
from itertools import pairwise

import pytest

from doc_extract.source import document as source
from doc_extract.source.layout import Cell, split_cells
from doc_extract.source.words import Word
from doc_extract.synth import pools, render
from doc_extract.synth.build import build
from doc_extract.synth.tiers import BY_NAME

#: Tiers chosen for what they stress in the *source* layer rather than in extraction: two rates and
#: fractional quantities put a long amount next to a bare quantity in every row, and a second page
#: is the case where the totals and the rows they summarise are not on the same page.
TIERS = ("clean", "mixed_rates", "grosz_rounding", "multi_page")

#: The two layouts that print an item table, and therefore the two where columns exist to be
#: confused. `compact` prints running text and is covered separately.
TABLE_TEMPLATES = ("classic", "ledger")


@pytest.fixture(scope="module")
def documents():
    """Every tier of `TIERS` in every layout, rendered once and read once."""
    read = {}
    for tier in TIERS:
        for template in render.TEMPLATES:
            built = build(BY_NAME[tier], seed=21_000, doc_id=tier, template=template)
            read[tier, template] = (built, source.read(render.render(built).data))
    return read


def cell_texts(document: source.SourceDocument) -> set[str]:
    return {document.text_of(span) for span in document.cells}


# --------------------------------------------------------------------------- offsets


def test_every_word_span_reproduces_its_own_text(documents):
    """The invariant M5 grounds on: a span is a slice of the text, not a parallel record of it."""
    for key, (_, document) in documents.items():
        for span in document.words:
            assert document.text[span.start:span.end].strip(), f"{key}: empty span {span}"
            assert "\t" not in document.text_of(span)
            assert "\n" not in document.text_of(span)


def test_cell_spans_cover_their_words_contiguously(documents):
    """A cell's text is the substring between its first and last word, separators included."""
    for key, (_, document) in documents.items():
        for span in document.cells:
            covered = document.text_of(span)
            assert covered == covered.strip(), f"{key}: {covered!r} is padded"
            assert "\t" not in covered and "\n" not in covered, f"{key}: {covered!r} spans fields"


def test_spans_are_ordered_and_do_not_overlap(documents):
    """Reading order is a property of the text, so the map has to agree with it."""
    for key, (_, document) in documents.items():
        for kind in ("words", "cells"):
            spans = getattr(document, kind)
            for earlier, later in pairwise(spans):
                assert earlier.end <= later.start, f"{key}: {kind} overlap at {earlier}"


def test_every_page_is_accounted_for(documents):
    for key, (_, document) in documents.items():
        pages = {span.page for span in document.words}
        assert pages == set(range(1, document.pages + 1)), key


def test_the_multi_page_tier_really_is_read_as_two_pages(documents):
    for template in render.TEMPLATES:
        _, document = documents["multi_page", template]
        assert document.pages >= 2, template
        assert source.PAGE_BREAK in document.text


def test_reading_the_same_bytes_twice_gives_the_same_document(documents):
    """A source layer that varied between runs would make a prompt hash worthless as provenance."""
    built, first = documents["mixed_rates", "classic"]
    again = source.read(render.render(built).data)
    assert again == first


# --------------------------------------------------------------------------- cells


def test_a_quantity_beside_a_price_stays_two_fields(documents):
    """The ambiguity M2 deliberately kept in the corpus, resolved here — the point of the layer.

    A flat text layer prints these as `3 466,62`, which reads as a single amount. Geometry keeps
    them apart, and this asserts it on every row of every table layout rather than on one example.
    """
    checked = 0
    for tier in TIERS:
        for template in TABLE_TEMPLATES:
            built, document = documents[tier, template]
            cells = cell_texts(document)
            for line in built.invoice.lines:
                quantity = render._quantity(line.quantity)
                price = render._price(line.unit_price_net)
                assert quantity in cells, f"{tier}/{template}: quantity {quantity!r} is not a field"
                assert price in cells, f"{tier}/{template}: price {price!r} is not a field"
                assert f"{quantity} {price}" not in cells, (
                    f"{tier}/{template}: {quantity!r} and {price!r} were read as one field"
                )
                checked += 1
    assert checked > 40, "too few rows to claim anything"


def test_an_amount_with_a_thousands_space_is_never_split_in_two(documents):
    """The other half of the same problem: the space inside `1 234,56` must not become a boundary.

    `pdfplumber` reports the two halves as separate words, so keeping them together is a real join
    rather than a no-op. The claim is made against the text and not against the cells because it has
    to hold in `compact` too, where there are no columns and a whole clause is one field — a
    boundary character anywhere inside the amount would show up here.
    """
    seen = 0
    for tier in TIERS:
        for template in render.TEMPLATES:
            built, document = documents[tier, template]
            for value in _amounts(built.invoice):
                printed = render._amount(value)
                if " " not in printed:
                    continue
                seen += 1
                assert printed in document.text, (
                    f"{tier}/{template}: {printed!r} was split across fields"
                )
    assert seen, "no rendered amount was large enough to carry a thousands separator"


def test_every_gold_amount_is_a_field_of_its_own_in_a_table_layout(documents):
    """Stronger than M2's `in text`: a whole field, not a substring of some larger reading."""
    for tier in TIERS:
        for template in TABLE_TEMPLATES:
            built, document = documents[tier, template]
            cells = cell_texts(document)
            missing = [
                render._amount(value)
                for value in _amounts(built.invoice)
                if render._amount(value) not in cells
            ]
            assert not missing, f"{tier}/{template} does not field {missing[:5]}"


def test_the_compact_layout_keeps_a_description_in_one_field(documents):
    """Running text has no columns, so a field is a whole phrase — and must not be shredded.

    The field is `1. Papier ksero A4 ...`: `compact` prints the row number and the description in
    one paragraph, and separating them is reading rather than layout. That the label travels with
    the value is the shape of the layer, not a defect — a cell is what the page shows as one thing.
    """
    built, document = documents["clean", "compact"]
    cells = cell_texts(document)
    missing = [
        line.description
        for line in built.invoice.lines
        if not any(cell.endswith(line.description) for cell in cells)
    ]
    assert not missing, missing


def test_an_identifier_stays_with_the_label_that_names_it(documents):
    """A NIP is one field, carrying the `NIP:` that identifies it — the page prints them together.

    Recorded as it is rather than as it would be convenient. The source layer reports what the page
    shows; stripping the label and the separators is reading, and reading is the extractor's job,
    which is exactly what the prompt asks it to do.
    """
    for template in render.TEMPLATES:
        built, document = documents["clean", template]
        printed = pools.format_nip(built.invoice.seller.nip)
        assert any(cell.endswith(printed) for cell in cell_texts(document)), template


# --------------------------------------------------------------------------- the threshold itself


def _word(text: str, *, x0: float, size: float = 8.0) -> Word:
    return Word(text=text, page=1, x0=x0, x1=x0 + 10, top=0, bottom=size, size=size)


def test_the_column_threshold_sits_between_a_space_and_a_column_gap():
    """The two populations the threshold separates, as numbers rather than as a claim.

    A space is 0.32 em (2.5 pt at 8 pt type) and a column gap is at least 12 pt, because
    `test_synth_render.py::test_no_cell_in_the_corpus_overruns_its_column` requires every value to
    fit its column with reportlab's 6 pt of padding on each side to spare. The threshold has to fall
    strictly between, and this is what would fail if either bound moved.
    """
    space = split_cells([_word("1", x0=0), _word("234,56", x0=10 + 2.5)])
    column = split_cells([_word("3", x0=0), _word("466,62", x0=10 + 12.0)])
    assert [cell.text for cell in space] == ["1 234,56"]
    assert [cell.text for cell in column] == ["3", "466,62"]


def test_a_wide_gap_at_a_large_size_is_still_one_field():
    """The threshold is in em, not points, or a heading's word spacing would read as two columns."""
    at_16pt = split_cells([_word("Faktura", x0=0, size=16), _word("korygująca", x0=10 + 5.0,
                                                                 size=16)])
    assert [cell.text for cell in at_16pt] == ["Faktura korygująca"]


def test_a_cell_reports_the_box_that_encloses_its_words():
    cell = Cell(words=(_word("1", x0=0), _word("234,56", x0=12)))
    assert (cell.x0, cell.x1) == (0, 22)


def _amounts(invoice) -> list[Decimal]:
    values = [invoice.total_gross]
    values += [total.net for total in invoice.rate_totals]
    values += [total.vat for total in invoice.rate_totals]
    values += [line.net for line in invoice.lines]
    values += [line.vat for line in invoice.lines]
    return values


def test_no_cell_contains_a_separator_this_layer_introduced(documents):
    """Whatever the page printed, the structural characters mean structure and nothing else."""
    for key, (_, document) in documents.items():
        for span in document.cells:
            assert not re.search(r"[\t\n]", document.text_of(span)), key
