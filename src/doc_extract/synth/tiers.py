"""The difficulty taxonomy: named, controlled ways an invoice gets harder to read correctly.

The point of generating a corpus rather than scraping one is that difficulty becomes a **variable
that can be held and varied**, so accuracy can be reported against it. A scraped corpus offers
"hard documents" only as an unlabelled mixture; here every document knows which trap it carries.

Each tier **names** one difficulty, and that is a weaker claim than isolating one. `reverse_charge`
does vary only its rates; the others move more than one knob. `mixed_rates` widens `line_range` to
fit four rate blocks; `multi_page` draws three rates alongside its 26-34 rows; `grosz_rounding`
draws two rates and fractional quantities as well as eight-decimal prices; `foreign_currency` adds
`0 WDT` on top of the currency, which is what an intra-EU invoice in EUR actually carries.

The consequence is worth stating rather than papering over: a drop on `multi_page` cannot be
attributed to pagination alone, because `mixed_rates` is the tier that owns multi-rate difficulty
and `multi_page` carries some of it too. A per-tier table built on these definitions reports which
*named difficulty* a document belonged to, not which single variable caused the loss. Attributing a
cause needs the tiers narrowed first — a deliberate open question, not an oversight.

Every tier is emitted in every layout (see `corpus`), so a per-tier result never confounds
difficulty with the template that happened to carry it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Tier:
    """One named difficulty. The fields are the knobs `build` reads; nothing else varies."""

    name: str
    description: str
    #: What the trap is, in the terms a reader of the results table needs.
    challenge: str
    kind: str                       #: RodzajFaktury
    rates: tuple[str, ...]          #: the rate codes line items may draw from
    line_range: tuple[int, int]     #: inclusive bounds on the number of rows
    currency: str = "PLN"
    #: Fractional digits on the unit price. `TKwotowy2` permits eight, and eight is what forces a
    #: line total to be a rounded figure rather than an exact product.
    price_decimals: int = 2
    #: Whether quantities may be fractional. Whole units keep `quantity x price` exact.
    fractional_quantities: bool = False
    #: Split payment is a payment mechanism, not a property of what is sold, so it cannot be
    #: derived from the line items the way reverse charge and exemption can.
    split_payment: bool = False


TIERS: tuple[Tier, ...] = (
    Tier(
        name="clean",
        description="One rate, whole quantities, round unit prices, a single page.",
        challenge="none — the control arm every other tier is read against",
        kind="VAT",
        rates=("23",),
        line_range=(2, 4),
    ),
    Tier(
        name="mixed_rates",
        description="Standard, both reduced rates and an exempt position in one document.",
        challenge="four rate blocks, each summed separately and attached to the right code",
        kind="VAT",
        rates=("23", "8", "5", "zw"),
        line_range=(4, 7),
    ),
    Tier(
        name="correction",
        description="Faktura korygująca: negative quantities and a negative total.",
        challenge="signs, plus a reference to a corrected invoice that is not this one's",
        kind="KOR",
        rates=("23",),
        line_range=(2, 3),
    ),
    Tier(
        name="advance",
        description="Faktura zaliczkowa documenting a payment received against an order.",
        challenge="the amount is a part payment, and an order value on the page is not the total",
        kind="ZAL",
        rates=("23",),
        line_range=(1, 2),
    ),
    Tier(
        name="reverse_charge",
        description="Odwrotne obciążenie: the buyer accounts for the tax, so VAT is zero.",
        challenge="a zero VAT column that is not a zero-rated sale, and an annotation that says so",
        kind="VAT",
        rates=("oo",),
        line_range=(2, 4),
    ),
    Tier(
        name="split_payment",
        description="Mechanizm podzielonej płatności, with the account it must be paid to.",
        challenge="a bank account and a mandatory annotation competing with the totals",
        kind="VAT",
        rates=("23",),
        line_range=(3, 5),
        split_payment=True,
    ),
    Tier(
        name="foreign_currency",
        description="Invoice in EUR with an NBP rate and the tax restated in PLN.",
        challenge="two currencies on one page; the PLN figures are not the invoice's amounts",
        kind="VAT",
        rates=("23", "0 WDT"),
        line_range=(3, 5),
        currency="EUR",
    ),
    Tier(
        name="grosz_rounding",
        description="Eight-decimal unit prices and fractional quantities.",
        challenge="no line total is an exact product; every one is a rounded figure",
        kind="VAT",
        rates=("23", "8"),
        line_range=(4, 8),
        price_decimals=8,
        fractional_quantities=True,
    ),
    Tier(
        name="multi_page",
        description="A long itemised invoice whose rows continue onto a second page.",
        challenge="the totals are separated from most of the rows they summarise",
        kind="VAT",
        rates=("23", "8", "5"),
        line_range=(26, 34),
    ),
)

BY_NAME: dict[str, Tier] = {tier.name: tier for tier in TIERS}
