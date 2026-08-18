"""The model enforces shape and closed domains — and deliberately does not enforce arithmetic.

That split is the design: a document whose numbers disagree must still be constructible, because
the project's whole purpose is to inspect, route and explain such documents. A model that refused
to exist could not be measured.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from pydantic import ValidationError

from doc_extract.schema.invariants import check
from doc_extract.schema.ksef import Invoice, LineItem, Party, RateTotal


def test_an_arithmetically_broken_invoice_still_constructs(invoice):
    """The load-bearing property: shape validation must not pre-empt the detector."""
    broken = Invoice(
        **{**invoice.model_dump(), "total_gross": Decimal("1.00")}
    )
    assert broken.total_gross == Decimal("1.00")
    assert check(broken) != ()


def test_unknown_vat_rate_is_rejected():
    with pytest.raises(ValidationError, match="closed domain"):
        RateTotal(rate="19", net=Decimal("100.00"), vat=Decimal("19.00"))


def test_unknown_invoice_kind_is_rejected(invoice):
    with pytest.raises(ValidationError, match="closed domain"):
        invoice.model_copy(update={}).model_validate(
            {**invoice.model_dump(), "kind": "PROFORMA"}
        )


def test_unknown_currency_is_rejected(invoice):
    with pytest.raises(ValidationError, match="closed domain"):
        Invoice.model_validate({**invoice.model_dump(), "currency": "XYZ"})


def test_unknown_field_is_rejected(invoice):
    """`extra="forbid"`: a drifted key from the extractor is a caught error, not silent data."""
    with pytest.raises(ValidationError):
        Invoice.model_validate({**invoice.model_dump(), "vat_total": "57.50"})


def test_models_are_frozen(invoice):
    with pytest.raises(ValidationError):
        invoice.total_gross = Decimal("0.00")


def test_money_is_limited_to_two_decimal_places():
    with pytest.raises(ValidationError):
        RateTotal(rate="23", net=Decimal("100.001"), vat=Decimal("23.00"))


def test_unit_price_admits_eight_decimal_places():
    """`TKwotowy2` — the schema's own asymmetry, and the reason the line rule needs a tolerance."""
    line = LineItem(line_no=1, quantity=Decimal("3"), unit_price_net=Decimal("0.33333333"))
    assert line.unit_price_net == Decimal("0.33333333")


def test_line_numbers_start_at_one():
    with pytest.raises(ValidationError):
        LineItem(line_no=0)


def test_empty_party_name_is_rejected():
    with pytest.raises(ValidationError):
        Party(name="   ")


def test_a_buyer_without_a_nip_is_valid():
    """FA(3) admits a consumer with no identifier; the model must not require one."""
    assert Party(name="Jan Kowalski").nip is None


def test_correction_flag_follows_the_kind(invoice):
    assert not invoice.is_correction
    assert Invoice.model_validate({**invoice.model_dump(), "kind": "KOR"}).is_correction


def test_a_minimal_invoice_needs_only_its_spine():
    """Lines and rate totals are optional: a simplified invoice (UPR) may carry neither."""
    minimal = Invoice(
        kind="UPR",
        number="FV/1",
        issue_date=dt.date(2026, 8, 10),
        currency="PLN",
        seller=Party(name="Acme sp. z o.o.", nip="1130220189"),
        buyer=Party(name="Jan Kowalski"),
        total_gross=Decimal("123.00"),
    )
    assert check(minimal) == ()
