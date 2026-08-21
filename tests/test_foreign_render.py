"""Every gold value has to be on the foreign page too, or the held-out set is not held-out.

This is the same obligation `tests/test_synth_render.py` carries, and it matters more here rather
than less. The whole purpose of M7's foreign corpus is to attribute a drop to the *page*: if one of
its three layouts quietly failed to print a field, every run over it would lose that field and the
loss would be reported as a model's failure to transfer. A held-out set that is unsolvable in places
measures its own defects.

So each amount, identifier, date and description is looked for in the text layer of the rendered
PDF, in the exact form that dialect prints it — driven off `model_fields` rather than a hand-written
list, so a field added to the gold cannot slip past unprinted.
"""

from __future__ import annotations

import dataclasses
import io
from decimal import Decimal

import pdfplumber
import pytest
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

from doc_extract.foreign import render
from doc_extract.foreign.dialect import BY_NAME, RATE_LABELS, TEMPLATES
from doc_extract.schema.checksums import strip_separators
from doc_extract.schema.ksef import Invoice, LineItem
from doc_extract.synth.build import build
from doc_extract.synth.tiers import TIERS

#: reportlab's `Table` default, 6 pt on each side. The width a cell has for its text is the column
#: minus this; leaving it out is what lets an over-wide value look like it fitted.
CELL_PADDING = 12.0

#: How each `LineItem` field reaches a foreign page, given that dialect's number format. `None`
#: marks a field a test of its own covers — the description word by word, the rate as a label.
LINE_FIELD_ON_PAGE = {
    "line_no": lambda speaker, value: str(value),
    "description": None,
    "quantity": lambda speaker, value: speaker.numbers.quantity(value),
    "unit_price_net": lambda speaker, value: speaker.numbers.price(value),
    "discount": lambda speaker, value: speaker.numbers.amount(value),
    "net": lambda speaker, value: speaker.numbers.amount(value),
    "vat": lambda speaker, value: speaker.numbers.amount(value),
    "vat_rate": None,
}

#: The same accounting for `Invoice`. `None` marks a field a test of its own covers: the parties and
#: the account are printed with separators and go through `strip_separators`, the collections are
#: covered field by field, and `kind` reaches the page as a title rather than as an FA(3) code.
INVOICE_FIELD_ON_PAGE = {
    "kind": None,
    "number": lambda speaker, value: str(value),
    "issue_date": lambda speaker, value: speaker.dates.format(value),
    "sale_date": lambda speaker, value: speaker.dates.format(value),
    "currency": lambda speaker, value: str(value),
    "seller": None,
    "buyer": None,
    "lines": None,
    "rate_totals": None,
    "total_gross": lambda speaker, value: speaker.numbers.amount(value),
    "payment_account": None,
}


@pytest.fixture(scope="module")
def pages():
    """One document per tier per foreign layout, rendered once and read once."""
    rendered = {}
    for tier in TIERS:
        for template in TEMPLATES:
            document = build(tier, seed=12_000, doc_id=tier.name, template=template)
            result = render.render(document)
            rendered[tier.name, template] = (document, result, _text(result.data))
    return rendered


def _text(data: bytes) -> str:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def test_every_field_of_the_models_is_accounted_for():
    """A gold field nobody decided to print is what these two maps exist to make impossible."""
    assert set(LineItem.model_fields) == set(LINE_FIELD_ON_PAGE)
    assert set(Invoice.model_fields) == set(INVOICE_FIELD_ON_PAGE)


def test_every_amount_in_the_gold_is_printed(pages):
    for (tier, template), (document, _, text) in pages.items():
        speaker = BY_NAME[template]
        invoice = document.invoice
        wanted: list[Decimal] = [invoice.total_gross]
        wanted += [total.net for total in invoice.rate_totals]
        wanted += [total.vat for total in invoice.rate_totals]
        wanted += [line.net for line in invoice.lines if line.net is not None]
        wanted += [line.vat for line in invoice.lines if line.vat is not None]
        missing = [str(value) for value in wanted if speaker.numbers.amount(value) not in text]
        assert not missing, f"{tier}/{template} does not print {missing[:5]}"


def test_every_line_item_value_is_printed(pages):
    for (tier, template), (document, _, text) in pages.items():
        speaker = BY_NAME[template]
        missing = [
            f"{name}={value}"
            for line in document.invoice.lines
            for name, formatter in LINE_FIELD_ON_PAGE.items()
            if formatter is not None
            and (value := getattr(line, name)) is not None
            and formatter(speaker, value) not in text
        ]
        assert not missing, f"{tier}/{template} does not print {missing[:5]}"


def test_every_invoice_level_value_is_printed(pages):
    for (tier, template), (document, _, text) in pages.items():
        speaker = BY_NAME[template]
        missing = [
            f"{name}={value}"
            for name, formatter in INVOICE_FIELD_ON_PAGE.items()
            if formatter is not None
            and (value := getattr(document.invoice, name)) is not None
            and formatter(speaker, value) not in text
        ]
        assert not missing, f"{tier}/{template} does not print {missing[:5]}"


def test_identifiers_reach_the_page_whatever_grouping_the_dialect_chose(pages):
    """The separators differ from the synthetic corpus's on purpose; the digits may not."""
    for (tier, template), (document, _, text) in pages.items():
        stripped = strip_separators(text)
        invoice = document.invoice
        wanted = [invoice.seller.nip, invoice.buyer.nip, invoice.payment_account]
        missing = [value for value in wanted if value and strip_separators(value) not in stripped]
        assert not missing, f"{tier}/{template} does not print {missing}"


def test_every_word_of_every_description_is_printed(pages):
    """Word by word rather than as one span: a description wraps, and a wrap is not a loss."""
    for (tier, template), (document, _, text) in pages.items():
        missing = [
            word
            for line in document.invoice.lines
            for word in (line.description or "").split()
            if word not in text
        ]
        assert not missing, f"{tier}/{template} does not print {missing[:5]}"


def test_every_rate_code_reaches_the_page_as_its_own_label(pages):
    for (tier, template), (document, _, text) in pages.items():
        codes = {line.vat_rate for line in document.invoice.lines if line.vat_rate}
        codes |= {total.rate for total in document.invoice.rate_totals}
        missing = [code for code in codes if RATE_LABELS[code] not in text]
        assert not missing, f"{tier}/{template} does not print {missing}"


def test_no_two_rate_codes_print_the_same_label():
    """The gold distinguishes `np I` from `np II`; a page that did not would be unreadable."""
    assert len(set(RATE_LABELS.values())) == len(RATE_LABELS)


def test_the_kind_reaches_the_page_as_a_distinguishable_title(pages):
    """`kind` is an FA(3) code and the page says it in words, so the words have to differ."""
    titles = {
        speaker.name: {speaker.title_vat, speaker.title_correction, speaker.title_advance}
        for speaker in map(BY_NAME.get, TEMPLATES)
    }
    for name, three in titles.items():
        assert len(three) == 3, f"{name} cannot state which kind of invoice it is"

    for (tier, template), (document, _, text) in pages.items():
        speaker = BY_NAME[template]
        expected = {
            "KOR": speaker.title_correction,
            "ZAL": speaker.title_advance,
        }.get(document.invoice.kind, speaker.title_vat)
        assert expected in text, f"{tier}/{template} does not state that it is a {expected}"


def test_every_label_a_dialect_declares_reaches_its_page(pages):
    """The reverse direction of every other test here, and the one that was missing.

    Everything else asserts that a *value* is printed. Nothing asserted that a **label** is, so
    `_slip` interpolating its internal role names put the English words `seller` and `buyer` on a
    third of the corpus while `Dostawca` and `Płatnik` reached no page at all — the opposite of what
    the package is for, invisible to a green suite, and biased in the flattering direction: an
    English role word is a stronger cue for an English-instructed model than an unfamiliar Polish
    one. It also caught a dialect declaring a label for the invoice number and printing the number
    without it.

    Case-insensitive because `slip` prints its labels lowercased and trailing, the way a receipt
    does. That is a style, not an absence: `dokument nr` is the label `Dokument nr`.
    Over the union of the tiers rather than per page, because a label is only printed when its
    field is: a correction's title reaches only a correction, and an account's label only an
    invoice that states one. What may not happen is a label reaching **no** page at all.
    """
    corpus: dict[str, str] = {}
    for (_, template), (_, _, text) in pages.items():
        corpus[template] = corpus.get(template, "") + "\n" + text.casefold()

    missing = [
        f"{template}: {label!r}"
        for template, folded in corpus.items()
        for label in BY_NAME[template].labels()
        if label.casefold() not in folded and not _wrapped_away(label, folded)
    ]
    assert not missing, sorted(missing)


def _wrapped_away(label: str, folded: str) -> bool:
    """Whether a multi-word label is on the page but broken across lines by its own column.

    Table headers are `Paragraph`s and fold inside their column, so `Wartość netto` arrives as two
    words on two lines. Every word being present is the most this can ask of a header without
    demanding columns wide enough to hold labels no reader needs on one line.
    """
    words = label.split()
    return len(words) > 1 and all(word.casefold() in folded for word in words)


def test_the_item_tables_fit_the_pages_they_are_printed_on():
    """An over-wide table is drawn past the edge silently and the last column simply disappears."""
    for template, widths in render.COLUMNS.items():
        printable = 210 - 2 * render.MARGIN[template]
        assert sum(widths) <= printable, template


def test_no_cell_in_the_corpus_overruns_its_column():
    """A column narrower than its content does not clip — it draws over the column beside it.

    This is not hypothetical here. `statement` merges the quantity with its unit into one cell, and
    at fifteen millimetres `10,968 mies.` was right-aligned straight through the position column
    beside it: `pdfplumber` then returned `110,968` as one word with one bounding box, fusing a line
    number to a quantity. Word geometry cannot separate that, so the value was on the page and
    unreadable — which would have been reported as a model failing to transfer to a foreign layout.

    Driven off `_row_cells` rather than a hand-written map, so a column reordered in a dialect
    cannot leave this test measuring the old positions.
    """
    render._register_fonts()
    too_wide = []
    for tier in TIERS:
        for template in TEMPLATES:
            if template not in render.COLUMNS:
                continue  # `slip` prints running text and has no columns to overrun
            speaker = BY_NAME[template]
            widths = render.COLUMNS[template]
            document = build(tier, seed=12_000, doc_id=tier.name, template=template)
            for index, line in enumerate(document.invoice.lines):
                cells = render._row_cells(line, render._unit(document.context, index), speaker)
                for position, text in enumerate(cells):
                    if position in render.WRAPPED_COLUMNS[template]:
                        continue  # a paragraph wraps; its own test covers the words it cannot
                    over = _overflow(text, widths[position], size=7.5)
                    if over > 0:
                        too_wide.append(
                            f"{tier.name}/{template} col {position}: {text!r} by {over:.1f} mm"
                        )
    assert not too_wide, too_wide[:8]


def test_every_wrapping_column_fits_the_longest_word_it_has_to_hold():
    """A `Paragraph` too narrow for one word splits the word instead of overrunning visibly.

    `wewnątrzwspólnotowa` becomes two fragments on two lines and is no longer on the page at all —
    no amount is lost, so the arithmetic still agrees, and only the description quietly stops being
    recoverable. Narrowing a wrapping column to make room for another is therefore not free.
    """
    render._register_fonts()
    descriptions = {
        word
        for tier in TIERS
        for document in [build(tier, seed=12_000, doc_id=tier.name, template=TEMPLATES[0])]
        for line in document.invoice.lines
        for word in (line.description or "").split()
    }
    #: Per column rather than pooled: the rate column never holds a product name and the description
    #: column never holds a rate, so measuring each against everything would demand a table twice as
    #: wide as the page for content it cannot receive.
    wanted = {
        (template, render.DESCRIPTION_COLUMN[template]): descriptions
        for template in render.COLUMNS
    } | {
        (template, render.RATE_COLUMN[template]): {
            word for label in RATE_LABELS.values() for word in label.split()
        }
        for template in render.COLUMNS
    }
    too_narrow = [
        f"{template} col {position}: {word!r} needs "
        f"{over + render.COLUMNS[template][position]:.1f} mm"
        for (template, position), words in wanted.items()
        for word in sorted(words)
        if (over := _overflow(word, render.COLUMNS[template][position], size=7.5)) > 0
    ]
    assert not too_narrow, too_narrow[:8]


def test_every_header_wraps_inside_its_own_column():
    """Headers are paragraphs too, so the requirement is the widest single word, not the string."""
    render._register_fonts()
    too_wide = [
        f"{template} col {index}: {word!r} overruns by {over:.1f} mm"
        for template, widths in render.COLUMNS.items()
        for index, header in enumerate(BY_NAME[template].columns)
        for word in header.split()
        if (over := _overflow(word, widths[index], size=7, font=render.BOLD)) > 0
    ]
    assert not too_wide, too_wide


def _overflow(text: str, column_mm: float, *, size: float, font: str = render.REGULAR) -> float:
    """How far past its column the text is drawn, in millimetres. Zero or less means it fits."""
    return (pdfmetrics.stringWidth(text, font, size) + CELL_PADDING) / mm - column_mm


def test_rendering_is_byte_for_byte_reproducible():
    """A corpus whose hashes moved between two runs of the generator could not be checksummed."""
    document = build(TIERS[0], seed=99, doc_id="repeat", template=TEMPLATES[0])
    assert render.render(document).data == render.render(document).data


def test_the_three_layouts_produce_genuinely_different_pages():
    """Three names over one page would make a per-layout table three readings of one thing."""
    texts = {
        template: _text(render.render(
            build(TIERS[0], seed=77, doc_id="differ", template=template)
        ).data)
        for template in TEMPLATES
    }
    assert len(set(texts.values())) == len(TEMPLATES)


def test_the_multi_page_tier_still_spills_onto_a_second_page():
    """The tier is defined by its pagination, so a layout that fitted it on one page loses it."""
    tier = next(tier for tier in TIERS if tier.name == "multi_page")
    for template in TEMPLATES:
        document = build(tier, seed=31, doc_id="long", template=template)
        assert render.render(document).pages >= 2, template


def test_polish_diacritics_survive_the_font():
    """All eighteen, driven through a description rather than hoped for in the catalogue.

    The family reportlab ships with is missing twelve of them, and a page set in it would drop them
    silently — a corpus with no `ą` and no `Ż` is easier to read in exactly the respect that
    matters. Asserting against whatever letters the seeded catalogue happened to draw would pass on
    a font that could only render half the alphabet.
    """
    alphabet = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"
    document = build(TIERS[0], seed=5, doc_id="letters", template=TEMPLATES[0])
    first = document.invoice.lines[0].model_copy(update={"description": alphabet})
    invoice = document.invoice.model_copy(update={"lines": (first, *document.invoice.lines[1:])})
    text = _text(render.render(
        dataclasses.replace(document, invoice=invoice)
    ).data)

    for character in alphabet:
        assert character in text, character
