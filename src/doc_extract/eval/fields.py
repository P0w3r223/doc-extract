"""What is scored, how two values of it are judged equal, and how an instance of it is identified.

An `Invoice` is not a flat record, and the difference matters to a metric. Seven of its fields are
singletons; six more belong to one of the two parties; the rest live inside collections whose
membership the extractor also has to get right. A scorer that walked the object naively would
compare `lines[0]` with `lines[0]` and call a correctly-read invoice wrong the moment a model
emitted the rows in a different order.

So a scored value has two names here. Its **field** is what it is — `lines[].net` — and that is what
a per-field table aggregates over. Its **key** is which one it is — the printed line number, or the
rate code — and that is what a prediction is matched on. `line_no` and `rate` are therefore *not*
scored fields: they are the identity, and misreading one is reported as the row being both missed
and spurious, which is a truer description than "the line number field was wrong".

**Equality is per field, not global.** Four rules cover every field, and each exists because a
plausible reading would otherwise be scored as an error:

* `AMOUNT` compares `Decimal` numerically, so `2.5` and `2.50` are the same quantity. They are the
  same figure on the page; the trailing zero is a formatting choice the schema does not fix.
* `IDENTIFIER` keeps alphanumerics and uppercases them, because `PL61 1090 1014` and
  `PL61109010140000071219812874` are the same account and `123-456-32-18` is the same NIP as
  `1234563218`. The wire format asks for separators to be removed; scoring a model down for
  obeying the page instead is measuring compliance, not reading.
* `TEXT` collapses runs of whitespace, because a name that wrapped across two lines of a PDF comes
  back with the break in it and a reader would call that the same name.
* `EXACT` is everything whose form is fixed by the standard — dates and closed-domain codes. There
  is nothing to normalise, and normalising would hide a real difference.

None of these forgive case, digits, or ordering *within* a value. `Acme` and `ACME` are different
readings, and a metric that called them equal would be unable to see a model that shouts.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from doc_extract.schema.ksef import Invoice, LineItem, Party, RateTotal

#: The key of a field that has only one instance per document.
SINGLETON = ""

_WHITESPACE = re.compile(r"\s+")
_NON_ALPHANUMERIC = re.compile(r"[^0-9A-Za-z]+")


class Match(StrEnum):
    """How two present values of a field are judged equal."""

    EXACT = "exact"
    AMOUNT = "amount"
    TEXT = "text"
    IDENTIFIER = "identifier"


class Group(StrEnum):
    """Which part of the document a field belongs to. The report is grouped by this."""

    HEADER = "header"
    SELLER = "seller"
    BUYER = "buyer"
    LINES = "lines"
    RATE_TOTALS = "rate_totals"


@dataclass(frozen=True, slots=True)
class Field:
    """One scored field: its name, how it is compared, and where on the document it lives."""

    name: str
    match: Match
    group: Group


@dataclass(frozen=True, slots=True)
class Value:
    """One instance of one field, as read out of an invoice.

    `value` is `None` for a field the invoice does not carry. That is a first-class outcome rather
    than a gap: an absent `discount` is the correct reading of a row with no discount printed, and
    a scorer that skipped `None` could not tell that reading apart from a missed one.
    """

    field: str
    key: str
    value: object | None


FIELDS: tuple[Field, ...] = (
    Field("kind", Match.EXACT, Group.HEADER),
    Field("number", Match.TEXT, Group.HEADER),
    Field("issue_date", Match.EXACT, Group.HEADER),
    Field("sale_date", Match.EXACT, Group.HEADER),
    Field("currency", Match.EXACT, Group.HEADER),
    Field("total_gross", Match.AMOUNT, Group.HEADER),
    Field("payment_account", Match.IDENTIFIER, Group.HEADER),
    Field("seller.name", Match.TEXT, Group.SELLER),
    Field("seller.nip", Match.IDENTIFIER, Group.SELLER),
    Field("seller.address", Match.TEXT, Group.SELLER),
    Field("buyer.name", Match.TEXT, Group.BUYER),
    Field("buyer.nip", Match.IDENTIFIER, Group.BUYER),
    Field("buyer.address", Match.TEXT, Group.BUYER),
    Field("lines[].description", Match.TEXT, Group.LINES),
    Field("lines[].quantity", Match.AMOUNT, Group.LINES),
    Field("lines[].unit_price_net", Match.AMOUNT, Group.LINES),
    Field("lines[].discount", Match.AMOUNT, Group.LINES),
    Field("lines[].net", Match.AMOUNT, Group.LINES),
    Field("lines[].vat", Match.AMOUNT, Group.LINES),
    Field("lines[].vat_rate", Match.EXACT, Group.LINES),
    Field("rate_totals[].net", Match.AMOUNT, Group.RATE_TOTALS),
    Field("rate_totals[].vat", Match.AMOUNT, Group.RATE_TOTALS),
)

BY_NAME: dict[str, Field] = {field.name: field for field in FIELDS}

#: The fields that identify an instance rather than carry one. Scored nowhere, matched on
#: everywhere — see the module docstring.
KEY_FIELDS: tuple[str, ...] = ("lines[].line_no", "rate_totals[].rate")


@dataclass(frozen=True, slots=True)
class Reading:
    """Every field instance of one invoice, keyed, with the collisions kept rather than dropped."""

    values: dict[tuple[str, str], object | None]
    #: Instances whose key was already taken — a repeated line number, a repeated rate code. Kept
    #: because a dict would silently discard them, and a row a prediction invented is exactly the
    #: kind of thing a metric must be able to report. `invariants` has its own opinion of the same
    #: documents; this one is about scoring, and neither is derived from the other.
    duplicates: tuple[Value, ...]

    def get(self, field: str, key: str) -> object | None:
        return self.values.get((field, key))

    def has(self, field: str, key: str) -> bool:
        return (field, key) in self.values


def read(invoice: Invoice) -> Reading:
    """Flatten an invoice into keyed field instances, in a stable order."""
    values: dict[tuple[str, str], object | None] = {}
    duplicates: list[Value] = []
    for instance in _walk(invoice):
        identity = (instance.field, instance.key)
        if identity in values:
            duplicates.append(instance)
            continue
        values[identity] = instance.value
    return Reading(values=values, duplicates=tuple(duplicates))


def _walk(invoice: Invoice) -> Iterator[Value]:
    yield Value("kind", SINGLETON, invoice.kind)
    yield Value("number", SINGLETON, invoice.number)
    yield Value("issue_date", SINGLETON, invoice.issue_date)
    yield Value("sale_date", SINGLETON, invoice.sale_date)
    yield Value("currency", SINGLETON, invoice.currency)
    yield Value("total_gross", SINGLETON, invoice.total_gross)
    yield Value("payment_account", SINGLETON, invoice.payment_account)
    yield from _party("seller", invoice.seller)
    yield from _party("buyer", invoice.buyer)
    for line in invoice.lines:
        yield from _line(line)
    for total in invoice.rate_totals:
        yield from _rate_total(total)


def _party(prefix: str, party: Party) -> Iterator[Value]:
    yield Value(f"{prefix}.name", SINGLETON, party.name)
    yield Value(f"{prefix}.nip", SINGLETON, party.nip)
    yield Value(f"{prefix}.address", SINGLETON, party.address)


def _line(line: LineItem) -> Iterator[Value]:
    key = str(line.line_no)
    yield Value("lines[].description", key, line.description)
    yield Value("lines[].quantity", key, line.quantity)
    yield Value("lines[].unit_price_net", key, line.unit_price_net)
    yield Value("lines[].discount", key, line.discount)
    yield Value("lines[].net", key, line.net)
    yield Value("lines[].vat", key, line.vat)
    yield Value("lines[].vat_rate", key, line.vat_rate)


def _rate_total(total: RateTotal) -> Iterator[Value]:
    yield Value("rate_totals[].net", total.rate, total.net)
    yield Value("rate_totals[].vat", total.rate, total.vat)


def equal(field: str, gold: object, predicted: object) -> bool:
    """Whether two *present* values of a field are the same reading.

    Absence is not handled here on purpose. "Both absent" and "one absent" are outcomes the scorer
    names, and folding them into an equality test would make a missed field indistinguishable from
    a correctly empty one.
    """
    match BY_NAME[field].match:
        case Match.AMOUNT:
            both = isinstance(gold, Decimal) and isinstance(predicted, Decimal)
            return both and gold == predicted
        case Match.TEXT:
            return _collapse(str(gold)) == _collapse(str(predicted))
        case Match.IDENTIFIER:
            return _identifier(str(gold)) == _identifier(str(predicted))
        case Match.EXACT:
            return gold == predicted


def _collapse(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def _identifier(text: str) -> str:
    return _NON_ALPHANUMERIC.sub("", text).upper()


def render(value: object | None) -> str | None:
    """A value as the string a prediction file and a report carry.

    `format(..., "f")` rather than `str`, for the same reason `wire` uses it: a `Decimal` that has
    been through exponent notation is a value a reader cannot compare by eye with the page.
    """
    match value:
        case None:
            return None
        case Decimal():
            return format(value, "f")
        case dt.date():
            return value.isoformat()
        case _:
            return str(value)
