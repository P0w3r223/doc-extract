"""The wire format, checked against the model it claims to mirror rather than beside it.

M2 learned this the expensive way: `discount` was in the gold, in the XML, and on no rendered
layout, and the test that would have caught it did not exist because the list of fields was written
by hand. Every accounting here is therefore driven off `model_fields`, so a field added to `Invoice`
fails a test instead of quietly never being asked for.

The other half is the round trip. A schema that describes the gold and a serialiser that produces it
are only useful if `Invoice` reads the result back as the same invoice — every amount, every
decimal place, every optional field that was absent still absent.
"""

from __future__ import annotations

import datetime as dt
import json
from decimal import Decimal

import pytest

from doc_extract.extract import wire
from doc_extract.schema import vocab
from doc_extract.schema.ksef import Invoice, LineItem, Party, RateTotal
from doc_extract.synth.corpus import documents

SCHEMA = wire.invoice_schema()

#: Every object in the schema, paired with the model whose fields it is supposed to mirror.
OBJECTS = {
    "invoice": (SCHEMA, Invoice),
    "seller": (SCHEMA["properties"]["seller"], Party),
    "lines": (SCHEMA["properties"]["lines"]["items"], LineItem),
    "rate_totals": (SCHEMA["properties"]["rate_totals"]["items"], RateTotal),
}


@pytest.mark.parametrize("name", sorted(OBJECTS))
def test_every_model_field_is_asked_for(name):
    shape, model = OBJECTS[name]
    assert set(shape["properties"]) == set(model.model_fields)


@pytest.mark.parametrize("name", sorted(OBJECTS))
def test_every_property_is_required_and_nothing_else_is_allowed(name):
    """Structured outputs enforce a schema only if the schema is closed and complete.

    "Absent" is therefore a null value rather than a missing key — which is also the honest shape:
    a document that does not state a sale date is a fact about the document, and a key that simply
    is not there is indistinguishable from a model that forgot to look.
    """
    shape, _ = OBJECTS[name]
    assert set(shape["required"]) == set(shape["properties"])
    assert shape["additionalProperties"] is False


def test_the_closed_domains_come_from_the_generated_vocabulary():
    """Transcribed enums would drift from the XSD the moment the Ministry republished it."""
    rates = SCHEMA["properties"]["rate_totals"]["items"]["properties"]["rate"]["enum"]
    kinds = SCHEMA["properties"]["kind"]["enum"]
    assert set(rates) == vocab.VAT_RATE_CODES
    assert set(kinds) == vocab.INVOICE_KINDS


def test_the_currency_is_not_enumerated():
    """A deliberate exception, recorded so that changing it is a decision rather than a drift.

    `TKodWaluty` is closed too, but it has 182 members and putting them in every prompt buys nothing
    the model was going to get wrong. It is still validated: `Invoice` rejects a code outside the
    domain, which makes a bad currency a schema repair rather than a silently accepted value.
    """
    assert "enum" not in SCHEMA["properties"]["currency"]
    with pytest.raises(ValueError, match="TKodWaluty"):
        Invoice.model_validate({**wire.serialise(_sample()), "currency": "XYZ"})


def test_every_amount_is_a_string_on_the_wire():
    """A JSON number is a float somewhere on some path, and `Decimal` money does not survive one."""
    payload = wire.serialise(_sample())
    for value in (payload["total_gross"], payload["lines"][0]["net"]):
        assert isinstance(value, str)
        assert " " not in value and "," not in value


def test_an_absent_field_serialises_as_null_rather_than_as_zero():
    """`P_10` is absent, not zero: printing `0,00` would put a number where the gold has none."""
    payload = wire.serialise(_sample())
    assert payload["lines"][0]["discount"] is None
    assert payload["sale_date"] is None


def test_the_serialiser_produces_exactly_the_keys_the_schema_declares():
    payload = wire.serialise(_sample())
    assert set(payload) == set(SCHEMA["properties"])
    assert set(payload["lines"][0]) == set(SCHEMA["properties"]["lines"]["items"]["properties"])
    assert set(payload["seller"]) == set(SCHEMA["properties"]["seller"]["properties"])


def test_the_round_trip_is_the_identity_on_the_corpus():
    """The claim M3 rests on: a perfect reading of a page comes back equal to the gold.

    Through `json.dumps` and back, so the encoding is exercised too — the diacritics, the negative
    amounts of a correction, and the eight-decimal unit prices of the rounding tier.
    """
    for document in documents(per_tier=1):
        payload = json.loads(json.dumps(wire.serialise(document.invoice), ensure_ascii=False))
        assert Invoice.model_validate(payload) == document.invoice, document.doc_id


def test_a_unit_price_keeps_all_eight_decimal_places():
    """`TKwotowy2` allows eight and the rounding tier uses them; two would be a different number."""
    price = Decimal("466.62345678")
    invoice = _sample(unit_price_net=price)
    assert wire.serialise(invoice)["lines"][0]["unit_price_net"] == "466.62345678"
    assert Invoice.model_validate(wire.serialise(invoice)).lines[0].unit_price_net == price


def _sample(**line_overrides) -> Invoice:
    line = LineItem(
        line_no=1, description="Usługa A", quantity=Decimal("2"),
        unit_price_net=Decimal("100.00"), net=Decimal("200.00"), vat=Decimal("46.00"),
        vat_rate="23",
    ).model_copy(update=line_overrides)
    return Invoice(
        kind="VAT",
        number="FV/2026/08/0001",
        issue_date=dt.date(2026, 8, 10),
        currency="PLN",
        seller=Party(name="Acme sp. z o.o.", nip="1130220189"),
        buyer=Party(name="Klient S.A."),
        lines=(line,),
        rate_totals=(RateTotal(rate="23", net=Decimal("200.00"), vat=Decimal("46.00")),),
        total_gross=Decimal("246.00"),
    )
