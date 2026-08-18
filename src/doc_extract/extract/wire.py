"""The JSON shape the model answers in, and the mapping between it and `schema.ksef.Invoice`.

**Every amount is a string.** Not because JSON cannot hold `1234.56`, but because the number of
places it might lose exactness on the way here is larger than the number of places this project
controls. `"1234.56"` is exact by construction on every path, in every SDK, through every proxy —
and `Decimal("1234.56")` is the same value the generator wrote. It also matches what the model is
actually doing: reading `1 234,56` off a page and normalising it, which is a string operation.

**Closed domains are enumerated; the currency is not.** `TRodzajFaktury` and `TStawkaPodatku` are
fourteen and seven values, and putting them in the schema is what makes an out-of-domain rate
impossible rather than merely wrong — which is the discipline `vocab` exists to enforce.
`TKodWaluty` has 182, and spending that on every prompt buys nothing the model was going to get
wrong: it is validated on arrival by `Invoice`, where a bad value becomes a schema repair.

**The property names are checked against the model, not maintained beside it.**
`tests/test_extract_wire.py` re-derives them from `model_fields`, so a field added to the gold is a
red test rather than a field the extractor was never asked for — the same accounting that caught
`discount` missing from every rendered layout in M2.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from decimal import Decimal

from doc_extract.schema import vocab
from doc_extract.schema.ksef import Invoice, LineItem, Party, RateTotal

#: What the model is told an absent field looks like. Structured outputs require every property to
#: be present, so "not on the document" has to be a value rather than a missing key.
ABSENT = None


def _nullable(shape: Mapping[str, object], description: str) -> dict[str, object]:
    return {"anyOf": [dict(shape), {"type": "null"}], "description": description}


def _string(description: str) -> dict[str, object]:
    return {"type": "string", "description": description}


_MONEY = "a plain decimal string, dot separator, no spaces or currency: \"1234.56\""

_PARTY = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name", "nip", "address"],
    "properties": {
        "name": _string("the party's name exactly as printed"),
        "nip": _nullable(
            {"type": "string"}, "ten digits, separators removed; null if the document states none"
        ),
        "address": _nullable({"type": "string"}, "street, postcode and city on one line"),
    },
}

_LINE_ITEM = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "line_no", "description", "quantity", "unit_price_net", "discount", "net", "vat", "vat_rate"
    ],
    "properties": {
        "line_no": {"type": "integer", "description": "1-based position in the item table"},
        "description": _nullable({"type": "string"}, "the goods or service, as printed"),
        "quantity": _nullable({"type": "string"}, "a decimal string; may be negative on a KOR"),
        "unit_price_net": _nullable(
            {"type": "string"}, f"net unit price, {_MONEY}; keep every printed decimal place"
        ),
        "discount": _nullable(
            {"type": "string"}, f"the discount on this row if one is printed, {_MONEY}"
        ),
        "net": _nullable({"type": "string"}, f"net value of the row, {_MONEY}"),
        "vat": _nullable({"type": "string"}, f"VAT amount of the row, {_MONEY}"),
        "vat_rate": _nullable(
            {"type": "string", "enum": sorted(vocab.VAT_RATE_CODES)},
            "the row's rate code; use the code, not the printed label",
        ),
    },
}

_RATE_TOTAL = {
    "type": "object",
    "additionalProperties": False,
    "required": ["rate", "net", "vat"],
    "properties": {
        "rate": {
            "type": "string",
            "enum": sorted(vocab.VAT_RATE_CODES),
            "description": "the rate code this block totals",
        },
        "net": _string(f"net summed over this rate, {_MONEY}"),
        "vat": _string(f"VAT summed over this rate, {_MONEY}"),
    },
}


def invoice_schema() -> dict[str, object]:
    """The output schema, built fresh so a caller cannot mutate a shared dict."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "kind", "number", "issue_date", "sale_date", "currency", "seller", "buyer",
            "lines", "rate_totals", "total_gross", "payment_account",
        ],
        "properties": {
            "kind": {
                "type": "string",
                "enum": sorted(vocab.INVOICE_KINDS),
                "description": "VAT unless the document says otherwise; KOR corrects, ZAL is a "
                               "part payment",
            },
            "number": _string("the invoice number as printed"),
            "issue_date": {
                "type": "string", "format": "date", "description": "data wystawienia, YYYY-MM-DD",
            },
            "sale_date": _nullable(
                {"type": "string", "format": "date"}, "data sprzedaży, YYYY-MM-DD; null if absent"
            ),
            "currency": _string("ISO 4217 code, e.g. PLN or EUR"),
            "seller": dict(_PARTY),
            "buyer": dict(_PARTY),
            "lines": {
                "type": "array",
                "description": "every row of the item table, in printed order, including rows that "
                               "continue onto a later page",
                "items": dict(_LINE_ITEM),
            },
            "rate_totals": {
                "type": "array",
                "description": "one entry per rate block in the summary; not the line items",
                "items": dict(_RATE_TOTAL),
            },
            "total_gross": _string(f"the gross total to pay, {_MONEY}"),
            "payment_account": _nullable(
                {"type": "string"},
                "the bank account, separators removed, with its PL prefix; null if absent",
            ),
        },
    }


# --------------------------------------------------------------------------- the other direction


def serialise(invoice: Invoice) -> dict[str, object]:
    """An `Invoice` in the shape the model is asked to produce.

    This is what makes a scripted model *perfect* rather than merely canned: M3's headline test
    sends the gold through this and requires the pipeline to give the same gold back, so the schema,
    the prompt's field names and the parser are checked against each other rather than by eye. M4
    reuses it as the oracle baseline B0 — the score an extractor would get if it read the page
    exactly right, which is not automatically 100 % and is worth measuring rather than assuming.
    """
    return {
        "kind": invoice.kind,
        "number": invoice.number,
        "issue_date": _date(invoice.issue_date),
        "sale_date": _date(invoice.sale_date),
        "currency": invoice.currency,
        "seller": _party(invoice.seller),
        "buyer": _party(invoice.buyer),
        "lines": [_line(line) for line in invoice.lines],
        "rate_totals": [_rate_total(total) for total in invoice.rate_totals],
        "total_gross": _amount(invoice.total_gross),
        "payment_account": invoice.payment_account,
    }


def _party(party: Party) -> dict[str, object]:
    return {"name": party.name, "nip": party.nip, "address": party.address}


def _line(line: LineItem) -> dict[str, object]:
    return {
        "line_no": line.line_no,
        "description": line.description,
        "quantity": _amount(line.quantity),
        "unit_price_net": _amount(line.unit_price_net),
        "discount": _amount(line.discount),
        "net": _amount(line.net),
        "vat": _amount(line.vat),
        "vat_rate": line.vat_rate,
    }


def _rate_total(total: RateTotal) -> dict[str, object]:
    return {"rate": total.rate, "net": _amount(total.net), "vat": _amount(total.vat)}


def _amount(value: Decimal | None) -> str | None:
    """`format(..., "f")` rather than `str`, so a value never leaves as `1E+2`."""
    return ABSENT if value is None else format(value, "f")


def _date(value: dt.date | None) -> str | None:
    return ABSENT if value is None else value.isoformat()
