"""Every gold value has to be on the page, or the extraction task is not solvable.

This is the test that keeps M4's numbers meaningful. If a field the metric scores were never
printed, no extractor could recover it, and the resulting score would measure the generator's
formatting rather than the model. So each amount, identifier and date is looked for in the text
layer of the rendered PDF, in the exact form the page prints it.

**What this does not claim.** Finding a value in `extract_text()` does not mean it can be *parsed*
out unambiguously. A quantity of 3 printed beside a price of 466,62 reads as `3 466,62`, because a
space is also Poland's thousands separator and a flat text dump has lost the column boundary. That
ambiguity is real — it is in real invoices too — and resolving it is the job of the source layer in
M3, which works from word geometry rather than a joined string. The corpus is not sanitised to hide
it.
"""

from __future__ import annotations

import io
import re
from dataclasses import replace
from decimal import Decimal

import pdfplumber
import pytest
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

from doc_extract.schema.checksums import strip_separators
from doc_extract.schema.ksef import Invoice, LineItem
from doc_extract.synth import pools, render
from doc_extract.synth.build import build
from doc_extract.synth.corpus import documents
from doc_extract.synth.tiers import BY_NAME, TIERS

#: reportlab's `Table` default, 6pt on each side. The width a cell has for its text is the column
#: minus this; leaving it out is what let an over-wide label look like it fitted.
CELL_PADDING = 12.0

#: How each `LineItem` field reaches the page. `None` marks a field checked by a test of its own —
#: the description word by word, the rate as a label. A field in neither place fails
#: `test_every_line_item_field_is_accounted_for`, so adding one to the gold forces the decision
#: rather than letting it default to unprinted, which is how `discount` came to be in the gold, in
#: the XML, and on no layout.
LINE_FIELD_ON_PAGE = {
    "line_no": str,
    "description": None,
    "quantity": render._quantity,
    "unit_price_net": render._price,
    "discount": render._amount,
    "net": render._amount,
    "vat": render._amount,
    "vat_rate": None,
}

#: The same accounting for `Invoice`. `None` again marks a field a test of its own covers: the two
#: parties and the account go through `strip_separators` because the page prints them formatted,
#: the collections are covered field by field via `LINE_FIELD_ON_PAGE` and the amount tests, and
#: `kind` reaches the page as a title rather than a code.
INVOICE_FIELD_ON_PAGE = {
    "kind": None,
    "number": str,
    "issue_date": lambda value: f"{value:%Y-%m-%d}",
    "sale_date": lambda value: f"{value:%Y-%m-%d}",
    "currency": str,
    "seller": None,
    "buyer": None,
    "lines": None,
    "rate_totals": None,
    "total_gross": render._amount,
    "payment_account": None,
}


@pytest.fixture(scope="module")
def pages():
    """One document per tier per template, rendered once and read once — the slow part of M2."""
    rendered = {}
    for tier in TIERS:
        for template in render.TEMPLATES:
            document = build(tier, seed=12_000, doc_id=tier.name, template=template)
            result = render.render(document)
            rendered[tier.name, template] = (document, result, _text(result.data))
    return rendered


def _text(data: bytes) -> str:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _printed(value: Decimal) -> str:
    return render._amount(value)


def test_every_amount_in_the_gold_is_printed(pages):
    for (tier, template), (document, _, text) in pages.items():
        invoice = document.invoice
        wanted = [invoice.total_gross]
        wanted += [total.net for total in invoice.rate_totals]
        wanted += [total.vat for total in invoice.rate_totals]
        wanted += [line.net for line in invoice.lines]
        wanted += [line.vat for line in invoice.lines]
        missing = [str(value) for value in wanted if _printed(value) not in text]
        assert not missing, f"{tier}/{template} does not print {missing[:5]}"


def test_every_line_item_field_is_accounted_for():
    """A gold field nobody decided to print is the failure this map exists to make impossible."""
    assert set(LineItem.model_fields) == set(LINE_FIELD_ON_PAGE)


def test_every_line_item_value_is_printed(pages):
    """Field by field off the model, so a field added to the gold cannot slip past unprinted.

    `discount` is why this is driven off `model_fields` rather than a hand-written list: it was
    drawn on 15.6 % of rows and folded into `net`, so a page without it stated
    `quantity x price != net`, and a reader who read that page perfectly still broke a hard
    invariant. The detector would have counted the generator's omission as the extractor's error.
    """
    for (tier, template), (document, _, text) in pages.items():
        missing = [
            f"{name}={value}"
            for line in document.invoice.lines
            for name, formatter in LINE_FIELD_ON_PAGE.items()
            if formatter is not None
            and (value := getattr(line, name)) is not None
            and formatter(value) not in text
        ]
        assert not missing, f"{tier}/{template} does not print {missing[:5]}"


def test_a_discounted_line_prints_the_discount_that_explains_its_net(pages):
    """Without it the page's own arithmetic contradicts itself — see the module docstring."""
    seen = 0
    for (tier, template), (document, _, text) in pages.items():
        for line in document.invoice.lines:
            if line.discount is None:
                continue
            seen += 1
            assert render._amount(line.discount) in text, (
                f"{tier}/{template} line {line.line_no}: net {line.net} is "
                f"{line.quantity} x {line.unit_price_net} less a discount of {line.discount}, "
                f"and the discount is not on the page"
            )
    assert seen, "no tier drew a discount — the test proves nothing"


def test_every_unit_price_is_printed_at_its_own_precision(pages):
    """A tidier two decimals would put a number on the page that is not the number in the gold."""
    for (tier, template), (document, _, text) in pages.items():
        missing = [
            str(line.unit_price_net)
            for line in document.invoice.lines
            if render._price(line.unit_price_net) not in text
        ]
        assert not missing, f"{tier}/{template} does not print {missing[:5]}"


def test_identifiers_and_dates_are_printed(pages):
    """Separators differ between the page and the gold, which is what `strip_separators` is for."""
    for (tier, template), (document, _, text) in pages.items():
        flat = strip_separators(text)
        invoice = document.invoice
        wanted = [
            invoice.number, invoice.seller.name, invoice.buyer.name,
            invoice.seller.nip, invoice.buyer.nip,
            f"{invoice.issue_date:%Y-%m-%d}", f"{invoice.sale_date:%Y-%m-%d}",
            invoice.currency, invoice.payment_account,
        ]
        missing = [str(v) for v in wanted if v and strip_separators(str(v)) not in flat]
        assert not missing, f"{tier}/{template} does not print {missing}"


def test_every_word_of_every_line_description_is_printed(pages):
    """Word by word, because a table cell wraps and the flat text layer interleaves the columns.

    A long description in `classic` or `ledger` occupies two lines of its cell, and the other
    columns of the row are drawn between them; `extract_text()` returns them in that visual order,
    so the description is on the page but not contiguous in the dump. Requiring contiguity here
    would be requiring the corpus to avoid a hazard real invoices have — the same reason the source
    layer in M3 reads word geometry rather than a joined string.
    """
    for (tier, template), (document, _, text) in pages.items():
        flat = re.sub(r"\s+", " ", text)
        missing = [
            word for line in document.invoice.lines
            for word in line.description.split()
            if word not in flat
        ]
        assert not missing, f"{tier}/{template} does not print {missing[:5]}"


def test_the_compact_template_keeps_a_description_in_one_piece(pages):
    """One layout has to be readable without geometry, or M3 has nothing simple to start from."""
    for tier, _template in [key for key in pages if key[1] == "compact"]:
        document, _, text = pages[tier, "compact"]
        flat = re.sub(r"\s+", " ", text)
        missing = [line.description for line in document.invoice.lines
                   if line.description not in flat]
        assert not missing, f"{tier}/compact does not print {missing[:3]} contiguously"


def test_the_item_table_fits_the_page_it_is_printed_on():
    """An over-wide table is drawn past the edge, silently — the last column simply disappears."""
    for template, widths in render.ITEM_COLUMNS.items():
        assert sum(widths) <= render.PRINTABLE[template], template


def _overflow(text: str, column_mm: float, *, font: str, size: float) -> float:
    """How far past its column the text is drawn, in millimetres. Zero or less means it fits."""
    return (pdfmetrics.stringWidth(text, font, size) + CELL_PADDING) / mm - column_mm


def test_every_fixed_content_column_fits_the_widest_value_it_could_ever_hold():
    """A column narrower than its content does not clip — it draws over the next column.

    `0% WDT` wanted 16.3 mm of an 11 mm column, and `pdfplumber` then returned it fused to the net
    beside it as ONE word with ONE bounding box. That is worse than the flat-text ambiguity this
    corpus deliberately keeps (a quantity of 3 beside a price of 466,62), because the source layer
    in M3 resolves that one from word geometry and cannot resolve this one at all.

    Measured against every label the vocabulary permits rather than the ones a tier happens to draw
    today, so `0 EX` — in the catalogue, in no tier — fails here instead of in a rendered corpus
    nobody re-reads.
    """
    render.register_fonts()
    fixed = {
        2: {item.unit for item in pools.CATALOGUE},
        render.PRICE_COLUMN: {render._price(Decimal("9999.12345678"))},
        7: set(render._RATE_LABELS.values()),
    }
    too_wide = [
        f"{layout} col {index}: {text!r} overruns by {over:.1f} mm"
        for layout, widths in render.ITEM_COLUMNS.items()
        for index, texts in fixed.items()
        for text in sorted(texts)
        if (over := _overflow(text, widths[index], font=render.REGULAR, size=8)) > 0
    ]
    assert not too_wide, too_wide


def test_the_description_column_fits_the_longest_word_in_the_catalogue():
    """The wrapping column fails differently from the others, and more quietly.

    A `Paragraph` whose column cannot hold a single word splits the word rather than overrunning,
    so `wewnątrzwspólnotowa` becomes two fragments on two lines and is no longer on the page. No
    amount is lost, so the arithmetic still checks out; only the description silently stops being
    recoverable. Narrowing this column to make room for another is therefore not free.
    """
    render.register_fonts()
    too_narrow = [
        f"{layout}: {word!r} needs {over + widths[render.DESCRIPTION_COLUMN]:.1f} mm"
        for layout, widths in render.ITEM_COLUMNS.items()
        for word in {w for item in pools.CATALOGUE for w in item.description.split()}
        if (over := _overflow(word, widths[render.DESCRIPTION_COLUMN],
                              font=render.REGULAR, size=7.5)) > 0
    ]
    assert not too_narrow, too_narrow


def test_every_header_wraps_inside_its_own_column():
    """Headers are `Paragraph`s, so the requirement is the widest single word, not the whole string.

    `Wartość netto` and `Kwota VAT` are both wider than the columns their values need, so as plain
    strings they overran exactly as an oversized value does — and a fused header is just as bad for
    a source layer trying to name columns.
    """
    render.register_fonts()
    too_wide = []
    for layout, widths in render.ITEM_COLUMNS.items():
        for index, header in enumerate(render.ITEM_HEADERS):
            for word in header.split():
                over = _overflow(word, widths[index], font=render.BOLD, size=render.HEADER_SIZE)
                if over > 0:
                    too_wide.append(f"{layout} col {index}: {word!r} overruns by {over:.1f} mm")
    assert not too_wide, too_wide


def test_no_cell_in_the_corpus_overruns_its_column():
    """The same check against what the corpus actually draws, which is where the amounts live.

    The widths above are bounded by the vocabulary; these are bounded by the seed. Both matter: a
    tier that starts drawing larger amounts is a silent layout change, and the manifest would
    record a new hash without anyone knowing why.
    """
    render.register_fonts()
    too_wide = []
    for document in documents():
        if document.template not in render.ITEM_COLUMNS:
            continue  # `compact` prints running text, so it has no columns to overrun
        widths = render.ITEM_COLUMNS[document.template]
        for line, unit in zip(document.invoice.lines, document.context.line_units, strict=True):
            cells = {
                0: str(line.line_no), 2: unit, 3: render._quantity(line.quantity),
                4: render._price(line.unit_price_net), 5: render._discount(line.discount),
                6: render._amount(line.net), 7: render._RATE_LABELS[line.vat_rate],
                8: render._amount(line.vat),
            }
            for index, text in cells.items():
                over = _overflow(text, widths[index], font=render.REGULAR, size=8)
                if over > 0:
                    too_wide.append(
                        f"{document.doc_id}/{document.template} col {index}: "
                        f"{text!r} overruns by {over:.1f} mm"
                    )
        for total in document.invoice.rate_totals if document.template == "ledger" else ():
            summary = {
                1: f"Razem {render._RATE_LABELS[total.rate]}", 6: render._amount(total.net),
                7: render._RATE_LABELS[total.rate], 8: render._amount(total.vat),
            }
            for index, text in summary.items():
                over = _overflow(text, widths[index], font=render.REGULAR, size=8)
                if over > 0:
                    too_wide.append(
                        f"{document.doc_id}/{document.template} summary col {index}: "
                        f"{text!r} overruns by {over:.1f} mm"
                    )
    assert not too_wide, too_wide[:8]


def test_polish_diacritics_survive_the_font(pages):
    """The fonts reportlab ships with are missing twelve of the eighteen accented letters."""
    _, _, text = pages["mixed_rates", "classic"]
    assert "ł" in text or "ą" in text or "ż" in text
    assert "usług" in text.lower() or "wartość" in text.lower()


def test_rendering_is_byte_for_byte_reproducible():
    """A corpus whose bytes changed on every run could not be checksummed in a manifest."""
    document = build(TIERS[0], seed=13_000, doc_id="d", template="classic")
    assert render.render(document).data == render.render(document).data


def test_the_multi_page_tier_actually_spills_onto_a_second_page():
    for template in render.TEMPLATES:
        document = build(BY_NAME["multi_page"], seed=14_000, doc_id="m", template=template)
        assert render.render(document).pages >= 2, template


def test_a_short_invoice_stays_on_one_page():
    document = build(BY_NAME["clean"], seed=15_000, doc_id="c", template="classic")
    assert render.render(document).pages == 1


def test_the_three_templates_produce_genuinely_different_pages():
    """Three layouts that rendered alike would buy none of the coverage they cost."""
    document = BY_NAME["mixed_rates"]
    texts = {
        template: _text(render.render(
            build(document, seed=16_000, doc_id="t", template=template)
        ).data)
        for template in render.TEMPLATES
    }
    assert len(set(texts.values())) == len(render.TEMPLATES)


def test_the_totals_are_not_the_first_numbers_on_the_page(pages):
    """A page whose total led the document would make position alone a good enough extractor."""
    document, _, text = pages["clean", "classic"]
    total = _printed(document.invoice.total_gross)
    first_line_net = _printed(document.invoice.lines[0].net)
    assert text.index(first_line_net) < text.index(total)


def test_no_two_rate_codes_print_the_same_label():
    """`fa3_xml` refuses to write a rate the document could not state unambiguously.

    A renderer that collapsed `np I` and `np II` into one label would reintroduce on the page the
    ambiguity the XML side rejects: the gold would distinguish two values no reader of the document
    could. No tier draws either code today, which is exactly why an assertion is worth more than
    the observation that it does not currently matter.
    """
    labels = list(render._RATE_LABELS.values())
    assert len(set(labels)) == len(labels), sorted(
        label for label in labels if labels.count(label) > 1
    )


def test_every_invoice_field_is_accounted_for():
    """The `LineItem` map caught `discount`; the same accounting has to cover the invoice itself."""
    assert set(Invoice.model_fields) == set(INVOICE_FIELD_ON_PAGE)


def test_every_invoice_value_is_printed(pages):
    """Driven off `model_fields`, so a field added to the gold cannot default to unprinted."""
    for (tier, template), (document, _, text) in pages.items():
        missing = [
            f"{name}={value}"
            for name, formatter in INVOICE_FIELD_ON_PAGE.items()
            if formatter is not None
            and (value := getattr(document.invoice, name)) is not None
            and formatter(value) not in text
        ]
        assert not missing, f"{tier}/{template} does not print {missing}"


def test_the_title_distinguishes_the_kinds_the_corpus_draws(pages):
    """`kind` reaches the page as a title, so the titles must not collapse two kinds into one.

    Only `VAT`, `KOR` and `ZAL` are drawn today, and each gets its own wording. `UPR` and `ROZ`
    would both render as the bare "Faktura" — recorded here rather than fixed, because no tier
    produces them and a title for a document the corpus cannot contain would be untested prose.
    """
    titles = {document.invoice.kind: render._title(document.invoice)
              for document, _, _ in pages.values()}
    assert len(set(titles.values())) == len(titles), titles


def test_an_invoice_without_a_sale_date_still_renders():
    """`sale_date` is optional in the schema, and formatting `None` raises rather than printing.

    `build` always sets one, so the corpus never exercises this — but the renderer is handed an
    `Invoice`, not a generated document, and M7's real held-out set is a poor place to find out.
    """
    for template in render.TEMPLATES:
        document = build(BY_NAME["clean"], seed=17_000, doc_id="n", template=template)
        without = replace(
            document, invoice=document.invoice.model_copy(update={"sale_date": None})
        )
        assert render.render(without).pages == 1
        assert "Data sprzedaży" not in _text(render.render(without).data)
