"""A documented subset of the KSeF FA(3) invoice, as frozen Pydantic models.

**This is a subset, deliberately.** FA(3) covers attachments, VAT groups, margin schemes, new
means of transport, order scopes and much else; modelling all of it would be transcription, not
engineering. What is here is the spine every invoice carries — parties, dates, currency, line
items, per-rate totals, and the gross total — which is also everything the invariants need.
Fields outside the subset are simply absent; nothing pretends they do not exist in the standard.

**What raises here, and what does not.** These models enforce only what makes a document
meaningless if violated: types, decimal places, and the closed domains of `vocab`. Cross-field
consistency — gross equalling net plus VAT, lines summing to their rate totals, a check digit
holding — is *not* enforced here. It is reported as data by `invariants`, because the whole point
of the project is to inspect documents that fail those rules. A model that refuses to be
constructed cannot be routed, measured, or explained to a reviewer.

Field names keep their FA(3) identifiers in the docstrings (`P_2`, `P_13_1`, …) so the mapping to
the standard stays checkable; the Python names are readable because the extractor's prompt and
the metrics both use them.

Money is `Decimal` throughout, never `float`. Every amount in the standard is a decimal with two
fractional digits and is compared for exact equality by the invariants.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from doc_extract.schema import vocab

#: `TKwotowy` — every monetary amount in FA(3).
Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2)]
#: `TKwotowy2` — unit price, carrying eight fractional digits where totals carry two.
UnitPrice = Annotated[Decimal, Field(max_digits=22, decimal_places=8)]
#: `TIlosci` — quantity.
Quantity = Annotated[Decimal, Field(max_digits=22, decimal_places=6)]

NonEmpty = Annotated[str, Field(min_length=1, max_length=512)]


class _Frozen(BaseModel):
    """Immutable, closed to unknown fields — a stray key is a caught error, not silent data."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class Party(_Frozen):
    """`Podmiot1` (seller) or `Podmiot2` (buyer).

    The buyer's NIP is optional because FA(3) admits a consumer with no identifier at all; the
    seller is always a Polish VAT taxpayer and always has one. Whether a present NIP *passes its
    check digit* is an invariant, not a constraint — an extractor that misreads a digit must
    still produce a `Party` that can be inspected.
    """

    name: NonEmpty
    nip: str | None = None
    address: str | None = Field(default=None, max_length=512)


class LineItem(_Frozen):
    """One `FaWiersz` row.

    `net`, `vat` and `unit_price` are all optional in the standard — a line may state a gross
    unit price instead, and simplified invoices omit most of the row. Absence is therefore not an
    error; it is a reason a given invariant does not apply to this line.
    """

    line_no: int = Field(ge=1)                    #: NrWierszaFa
    description: NonEmpty | None = None           #: P_7
    quantity: Quantity | None = None              #: P_8B
    unit_price_net: UnitPrice | None = None       #: P_9A
    discount: Money | None = None                 #: P_10
    net: Money | None = None                      #: P_11
    vat: Money | None = None                      #: P_11Vat
    vat_rate: str | None = None                   #: P_12, a TStawkaPodatku code

    @field_validator("vat_rate")
    @classmethod
    def _known_rate(cls, value: str | None) -> str | None:
        if value is not None and value not in vocab.VAT_RATE_CODES:
            raise ValueError(f"unknown VAT rate code {value!r}; TStawkaPodatku is a closed domain")
        return value


class RateTotal(_Frozen):
    """One `P_13_x` / `P_14_x` pair: the net and VAT summed over a single rate.

    The XSD groups each pair in an optional `<xsd:sequence minOccurs="0">`, so a rate is either
    absent entirely or present with both halves — which is why this is one model and not two
    loose fields. Untaxed codes still carry a net amount, with VAT of zero.
    """

    rate: str
    net: Money
    vat: Money

    @field_validator("rate")
    @classmethod
    def _known_rate(cls, value: str) -> str:
        if value not in vocab.VAT_RATE_CODES:
            raise ValueError(f"unknown VAT rate code {value!r}; TStawkaPodatku is a closed domain")
        return value


class Invoice(_Frozen):
    """`Faktura` reduced to its spine: who, when, in what currency, for how much.

    `total_gross` is `P_15`. The standard stores it as a plain decimal with no stated relationship
    to the rate totals or the lines — the XSD contains no assertions of any kind — which is
    exactly the gap the invariants fill.
    """

    kind: str                                     #: RodzajFaktury
    number: NonEmpty                              #: P_2
    issue_date: dt.date                           #: P_1
    sale_date: dt.date | None = None              #: P_6
    currency: str                                 #: KodWaluty
    seller: Party                                 #: Podmiot1
    buyer: Party                                  #: Podmiot2
    lines: tuple[LineItem, ...] = ()              #: FaWiersz
    rate_totals: tuple[RateTotal, ...] = ()       #: P_13_x / P_14_x
    total_gross: Money                            #: P_15
    payment_account: str | None = None            #: Platnosc/RachunekBankowy/NrRB

    @field_validator("kind")
    @classmethod
    def _known_kind(cls, value: str) -> str:
        if value not in vocab.INVOICE_KINDS:
            raise ValueError(f"unknown invoice kind {value!r}; RodzajFaktury is a closed domain")
        return value

    @field_validator("currency")
    @classmethod
    def _known_currency(cls, value: str) -> str:
        if value not in vocab.CURRENCIES:
            raise ValueError(f"unknown currency {value!r}; TKodWaluty is a closed domain")
        return value

    @property
    def is_correction(self) -> bool:
        """Corrections may carry negative amounts legitimately; other kinds may not."""
        return self.kind in vocab.CORRECTION_KINDS
