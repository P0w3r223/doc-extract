"""B2 reads real rendered pages, and its limits are pinned rather than described.

The pattern baseline is only worth reporting if two things are true: it genuinely reads the three
layouts, and its failures are the structural ones its docstring claims. Both are tested here on
pages rendered by `synth`, not on hand-written fixtures — a regular expression tested against a
string somebody typed proves nothing about a PDF.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from doc_extract.eval import pattern
from doc_extract.source import document as source_document
from doc_extract.synth import render
from doc_extract.synth.build import build
from doc_extract.synth.tiers import BY_NAME


def _page(tier: str, template: str, seed: int = 11):
    document = build(BY_NAME[tier], seed=seed, doc_id=f"{tier}-test", template=template)
    source = source_document.read(render.render(document).data)
    return document.invoice, pattern.read(source.text)


@pytest.mark.parametrize("template", render.TEMPLATES)
def test_the_header_is_read_from_every_layout(template):
    invoice, read = _page("clean", template)

    assert read["number"] == invoice.number
    assert read["kind"] == invoice.kind
    assert read["issue_date"] == invoice.issue_date.isoformat()
    assert read["sale_date"] == (invoice.sale_date and invoice.sale_date.isoformat())
    assert read["currency"] == invoice.currency
    assert Decimal(read["total_gross"]) == invoice.total_gross


@pytest.mark.parametrize("template", render.TEMPLATES)
def test_both_parties_are_read_however_the_layout_arranges_them(template):
    """Side by side, stacked under headings, or an unlabelled letterhead: three arrangements."""
    invoice, read = _page("clean", template)

    assert read["seller"]["name"] == invoice.seller.name
    assert read["seller"]["nip"] == invoice.seller.nip
    assert read["buyer"]["name"] == invoice.buyer.name
    assert read["buyer"]["nip"] == invoice.buyer.nip
    assert read["seller"]["address"] == invoice.seller.address


@pytest.mark.parametrize("template", render.TEMPLATES)
def test_the_rate_blocks_come_back_as_codes_and_not_as_printed_labels(template):
    """`0% WDT` on the page is `0 WDT` in the standard; a baseline that reported the label would be
    inventing a value outside the closed domain, which `Invoice` would reject."""
    invoice, read = _page("foreign_currency", template)

    assert [total["rate"] for total in read["rate_totals"]] == [
        total.rate for total in invoice.rate_totals
    ]
    assert [Decimal(total["net"]) for total in read["rate_totals"]] == [
        total.net for total in invoice.rate_totals
    ]


@pytest.mark.parametrize("template", render.TEMPLATES)
def test_the_amounts_are_normalised_out_of_the_polish_convention(template):
    """`1 234,56` is one amount, and the thousands space is not a column break."""
    _, read = _page("multi_page", template)
    for line in read["lines"]:
        assert " " not in (line["net"] or "")
        assert Decimal(line["net"])


def test_a_row_carrying_its_own_number_is_matched_to_the_gold_row():
    invoice, read = _page("clean", "compact")
    by_number = {line["line_no"]: line for line in read["lines"]}

    for line in invoice.lines:
        assert Decimal(by_number[line.line_no]["net"]) == line.net
        assert by_number[line.line_no]["vat_rate"] == line.vat_rate


def test_the_discount_column_shifts_a_table_row_and_that_is_the_known_limit():
    """The failure the docstring claims, pinned so it cannot quietly become something else.

    `P_10` prints as an empty cell when absent, and an empty cell leaves no trace in the text layer.
    A reader counting columns from the right therefore takes the discount for the net value on
    exactly the rows that carry one — while the *totals* stay right, which is what makes these rows
    a useful error for M5 and not merely a bug.
    """
    tier, template = "clean", "classic"
    for seed in range(60):
        document = build(BY_NAME[tier], seed=seed, doc_id="probe", template=template)
        discounted = [line for line in document.invoice.lines if line.discount is not None]
        if not discounted:
            continue

        source = source_document.read(render.render(document).data)
        read = pattern.read(source.text)
        rows = {row["line_no"]: row for row in read["lines"]}
        row = rows[discounted[0].line_no]

        assert Decimal(row["net"]) == discounted[0].net, "the net value is still read correctly"
        assert Decimal(row["quantity"]) != discounted[0].quantity, (
            "the quantity is read out of the wrong column — this is the documented limit"
        )
        return
    pytest.fail("no discounted row was generated in 60 seeds; the probe needs widening")


def test_nothing_is_invented_when_nothing_matches():
    """An unmatched field is `None` and is refused by `Invoice`; a plausible default would be scored
    as if it had been read."""
    read = pattern.read("Nothing here resembles an invoice.")

    assert read["number"] is None
    assert read["total_gross"] is None
    assert read["payment_account"] is None
    assert read["lines"] == []
    assert read["rate_totals"] == []
