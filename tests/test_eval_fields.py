"""What the scorer considers a field, and when it considers two readings the same.

The equality rules are the part of a metric that quietly decides what the numbers mean. Each one
below exists because a plausible, correct reading would otherwise be counted as an error — or,
worse, because a wrong one would be counted as right.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from doc_extract.eval import fields
from doc_extract.schema.ksef import Invoice, LineItem, Party, RateTotal


def test_every_declared_field_is_read_from_a_full_invoice(invoice):
    """A field nobody reads is a column of dashes; one nobody declared is silently unmeasured."""
    reading = fields.read(invoice)
    read_names = {name for name, _ in reading.values}
    assert read_names == {field.name for field in fields.FIELDS}


def test_collections_are_keyed_by_the_document_and_not_by_position(invoice):
    reading = fields.read(invoice)
    line_keys = {key for name, key in reading.values if name == "lines[].net"}
    rate_keys = {key for name, key in reading.values if name == "rate_totals[].vat"}
    assert line_keys == {"1", "2", "3"}
    assert rate_keys == {"23", "8"}


def test_the_key_fields_are_not_scored():
    """`line_no` and `rate` identify a row; scoring them would double-count the same mistake."""
    assert not set(fields.KEY_FIELDS) & set(fields.BY_NAME)


def test_a_repeated_key_is_kept_rather_than_overwritten(invoice):
    """A dict would drop the second row silently, and an invented row is exactly what to report."""
    doubled = invoice.model_copy(update={"lines": (*invoice.lines, invoice.lines[0])})
    reading = fields.read(doubled)

    assert len(reading.values) == len(fields.read(invoice).values)
    assert {value.field for value in reading.duplicates} == {
        field.name for field in fields.FIELDS if field.name.startswith("lines[]")
    }


@pytest.mark.parametrize(
    ("field", "gold", "predicted", "same"),
    [
        # An amount is a quantity, not a string: the trailing zero is formatting.
        ("total_gross", Decimal("2.5"), Decimal("2.50"), True),
        ("total_gross", Decimal("2.5"), Decimal("2.51"), False),
        # An identifier is the same identifier however the page happened to punctuate it.
        ("seller.nip", "1130220189", "113-022-01-89", True),
        ("payment_account", "PL61109010140000071219812874", "PL61 1090 1014 0000 0712 1981 2874",
         True),
        ("seller.nip", "1130220189", "1130220188", False),
        # A name that wrapped across two lines is the same name; a different name is not.
        ("seller.name", "Acme sp. z o.o.", "Acme\n sp.  z o.o.", True),
        ("seller.name", "Acme sp. z o.o.", "Acme sp. z o. o.", False),
        # Case is a reading difference. A metric that forgave it could not see a model that shouts.
        ("buyer.name", "Klient S.A.", "KLIENT S.A.", False),
        # Closed domains and dates are fixed by the standard; there is nothing to normalise.
        ("currency", "PLN", "pln", False),
        ("issue_date", dt.date(2026, 8, 10), dt.date(2026, 8, 10), True),
        ("issue_date", dt.date(2026, 8, 10), dt.date(2026, 8, 11), False),
    ],
)
def test_equality_is_decided_per_field(field, gold, predicted, same):
    assert fields.equal(field, gold, predicted) is same


def test_rendering_never_produces_exponent_notation():
    """`1E+2` in a prediction file is a number a reader cannot compare with the page."""
    assert fields.render(Decimal("1E+2")) == "100"
    assert fields.render(Decimal("0.00000001")) == "0.00000001"
    assert fields.render(dt.date(2026, 2, 1)) == "2026-02-01"
    assert fields.render(None) is None


def test_an_absent_optional_field_is_read_as_none_rather_than_skipped():
    """`None` is a reading of the document, and the scorer needs to see it to judge it."""
    invoice = Invoice(
        kind="VAT",
        number="FV/1",
        issue_date=dt.date(2026, 1, 1),
        currency="PLN",
        seller=Party(name="A"),
        buyer=Party(name="B"),
        lines=(LineItem(line_no=1, net=Decimal("10.00")),),
        rate_totals=(RateTotal(rate="23", net=Decimal("10.00"), vat=Decimal("2.30")),),
        total_gross=Decimal("12.30"),
    )
    reading = fields.read(invoice)

    assert reading.has("lines[].discount", "1")
    assert reading.get("lines[].discount", "1") is None
    assert reading.get("sale_date", fields.SINGLETON) is None
