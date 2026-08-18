"""Turn a seed and a difficulty tier into one invoice, together with everything needed to print it.

Two objects come out, and the split between them is the important part.

`Invoice` is the **gold** — the frozen FA(3) subset an extractor is asked to recover, and the only
thing a metric ever compares against. `Context` is everything else a real document carries: the
issuing place, the payment terms, the exchange rate, the reference to a corrected invoice, the
annotation flags. Those appear on the page and in the XML, they make the document realistic and
they make extraction harder — but they are not scored, so keeping them out of `Invoice` stops a
metric from silently acquiring fields nobody decided to measure.

**The gold is arithmetically coherent by construction, and that is asserted, not assumed.**
`tests/test_synth_build.py` runs `invariants.check()` over every document of every tier and
requires it to come back empty. If a tier could produce gold that breaks a hard rule, the detector
study in M5 would be measuring the generator instead of the extractor.
"""

from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass
from decimal import Decimal

from doc_extract.schema import vocab
from doc_extract.schema.ksef import Invoice, LineItem, Party, RateTotal
from doc_extract.synth import pools
from doc_extract.synth.money import apportion, round_money, total_of
from doc_extract.synth.rate_slots import order_of
from doc_extract.synth.tiers import Tier

#: The corpus sits inside the first year FA(3) was mandatory, so the documents are contemporary
#: with the standard they follow.
_FIRST_DAY = dt.date(2026, 2, 1)
_LAST_DAY = dt.date(2026, 11, 30)

#: Roughly what one line of a business invoice is worth, and the budget quantities are drawn to.
_LINE_BUDGET = Decimal(6_000)

_DISCOUNT_PROBABILITY = 0.15
_ACCOUNT_PROBABILITY = 0.8
_PAYMENT_TERM_DAYS = (7, 14, 21, 30, 60)


@dataclass(frozen=True, slots=True)
class Annotations:
    """The `Adnotacje` block, which FA(3) makes mandatory even when every flag is "no"."""

    exempt: bool
    reverse_charge: bool
    split_payment: bool
    cash_basis: bool
    self_billing: bool


@dataclass(frozen=True, slots=True)
class Context:
    """Everything the document carries that the extraction schema deliberately does not model."""

    seller: pools.Company
    buyer: pools.Company
    issued_at: dt.datetime
    place: str
    line_units: tuple[str, ...]
    payment_due: dt.date
    payment_form: tuple[str, str]
    bank_name: str
    annotations: Annotations
    fx_rate: Decimal | None = None
    fx_date: dt.date | None = None
    #: `P_14_xW` — the tax restated in PLN, aligned with `invoice.rate_totals`. Empty in PLN.
    vat_in_pln: tuple[Decimal, ...] = ()
    corrected_number: str | None = None
    corrected_date: dt.date | None = None
    correction_reason: str | None = None
    gross_before_correction: Decimal | None = None   #: P_15ZK
    order_value: Decimal | None = None


@dataclass(frozen=True, slots=True)
class Document:
    """One generated invoice: its gold, its trimmings, and the provenance of both."""

    doc_id: str
    tier: str
    template: str
    seed: int
    invoice: Invoice
    context: Context


def build(tier: Tier, *, seed: int, doc_id: str, template: str) -> Document:
    """One document, fully determined by `seed` — the same seed always yields the same invoice."""
    rng = random.Random(seed)
    seller_company = rng.choice(pools.SELLERS)
    buyer_company = rng.choice(pools.BUYERS)

    issue_date = _random_date(rng)
    sale_date = issue_date - dt.timedelta(days=rng.randint(0, 20))

    drafts = _draw_lines(tier, rng)
    lines, rate_totals = _reconcile(drafts, negative=tier.kind in vocab.CORRECTION_KINDS)
    total_gross = total_of([total.net + total.vat for total in rate_totals])

    account = (
        pools.iban(rng)
        if tier.split_payment or rng.random() < _ACCOUNT_PROBABILITY
        else None
    )

    invoice = Invoice(
        kind=tier.kind,
        number=_number(tier, issue_date, rng),
        issue_date=issue_date,
        sale_date=sale_date,
        currency=tier.currency,
        seller=Party(
            name=seller_company.name,
            nip=pools.nip(rng),
            address=seller_company.address_line,
        ),
        buyer=Party(
            name=buyer_company.name,
            nip=pools.nip(rng),
            address=buyer_company.address_line,
        ),
        lines=tuple(line for line, _ in lines),
        rate_totals=rate_totals,
        total_gross=total_gross,
        payment_account=account,
    )
    context = _context(
        tier, rng, seller_company, buyer_company, issue_date,
        units=tuple(unit for _, unit in lines),
        rate_totals=rate_totals,
        total_gross=total_gross,
    )
    return Document(
        doc_id=doc_id, tier=tier.name, template=template, seed=seed,
        invoice=invoice, context=context,
    )


# --------------------------------------------------------------------------- line items


@dataclass(frozen=True, slots=True)
class _Draft:
    """A row before its VAT is known — VAT is settled per rate group, not per row."""

    item: pools.Item
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal | None
    net: Decimal


def _draw_lines(tier: Tier, rng: random.Random) -> list[_Draft]:
    """Rows for this tier, with every one of its rates guaranteed to appear at least once.

    Without that guarantee a `mixed_rates` document could draw four rows at 23 % and quietly
    become a `clean` one, which would make the per-tier table meaningless.
    """
    count = max(rng.randint(*tier.line_range), len(tier.rates))
    rates = list(tier.rates) + [rng.choice(tier.rates) for _ in range(count - len(tier.rates))]
    rng.shuffle(rates)
    return [_draw_line(tier, rate, rng) for rate in rates]


def _draw_line(tier: Tier, rate: str, rng: random.Random) -> _Draft:
    item = rng.choice([entry for entry in pools.CATALOGUE if entry.vat_rate == rate])
    quantity = _draw_quantity(item, tier, rng)
    unit_price = _draw_price(item, tier, rng)
    #: Not a gross: everything here is net of VAT, which is settled per rate group in `_reconcile`.
    #: Naming it `gross_of_line` invited the reading that it was net + VAT, which is what `gross`
    #: means in every other name in this package, `total_gross` included.
    undiscounted_net = quantity * unit_price
    discount = (
        round_money(undiscounted_net * Decimal(rng.choice(("0.03", "0.05", "0.10"))))
        if rng.random() < _DISCOUNT_PROBABILITY
        else None
    )
    net = round_money(undiscounted_net - (discount or Decimal(0)))
    return _Draft(item=item, quantity=quantity, unit_price=unit_price, discount=discount, net=net)


def _draw_quantity(item: pools.Item, tier: Tier, rng: random.Random) -> Decimal:
    """Enough units to make a plausible line, and no more.

    Quantity is drawn against the item's own price rather than from a fixed range, so a nine
    thousand złoty security audit is bought once and copier paper by the pallet. A flat range
    produces six-figure line totals on expensive services, and an invoice whose amounts are
    obviously wrong teaches an extractor nothing about reading a real one.
    """
    midpoint = (item.min_price + item.max_price) / 2
    ceiling = max(1, min(40, int(_LINE_BUDGET / midpoint)))
    if tier.fractional_quantities:
        return Decimal(rng.randint(1_050, max(1_051, ceiling * 1_000))) / 1_000
    return Decimal(rng.randint(1, ceiling))


def _draw_price(item: pools.Item, tier: Tier, rng: random.Random) -> Decimal:
    """A price in the item's own range, at the tier's precision.

    Eight fractional digits are not decoration: `TKwotowy2` permits them while every total carries
    two, so an eight-decimal price makes `quantity x price` land off the grosz almost always. The
    rounding tier is therefore a property of the standard rather than a contrived one.
    """
    scale = 10 ** tier.price_decimals
    low = int(item.min_price * scale)
    high = int(item.max_price * scale)
    return Decimal(rng.randint(low, high)) / scale


def _reconcile(
    drafts: list[_Draft], *, negative: bool
) -> tuple[list[tuple[LineItem, str]], tuple[RateTotal, ...]]:
    """Settle VAT per rate group, then hand it back to the rows so both sums agree exactly.

    The tax is levied on the group's net total, which is what `P_14_x` means and what
    `invariants.totals.vat_matches_rate` checks. The per-row figures are then apportioned out of
    that total rather than rounded independently, so `invariants.lines.sum_matches_rate_vat` holds
    exactly while no row drifts more than a grosz from its own rate — see `money.apportion`.
    """
    sign = Decimal(-1) if negative else Decimal(1)
    by_rate: dict[str, list[tuple[int, _Draft]]] = {}
    for index, draft in enumerate(drafts):
        by_rate.setdefault(draft.item.vat_rate, []).append((index, draft))

    vats: dict[int, Decimal] = {}
    rate_totals: list[RateTotal] = []
    for rate, group in by_rate.items():
        fraction = vocab.RATE_FRACTION[rate]
        nets = [sign * draft.net for _, draft in group]
        rate_net = total_of(nets)
        rate_vat = round_money(rate_net * fraction)
        for (index, _), share in zip(group, apportion(rate_vat, [net * fraction for net in nets]),
                                     strict=True):
            vats[index] = share
        rate_totals.append(RateTotal(rate=rate, net=rate_net, vat=rate_vat))

    #: Listed in the order FA(3) lays the `P_13_x` blocks out, not the order the rows were drawn.
    #: The document can only say one of the two, so the gold has to agree with the document.
    rate_totals.sort(key=lambda total: order_of(total.rate))

    lines = [
        (
            LineItem(
                line_no=index + 1,
                description=draft.item.description,
                quantity=sign * draft.quantity,
                unit_price_net=draft.unit_price,
                discount=sign * draft.discount if draft.discount is not None else None,
                net=sign * draft.net,
                vat=vats[index],
                vat_rate=draft.item.vat_rate,
            ),
            draft.item.unit,
        )
        for index, draft in enumerate(drafts)
    ]
    return lines, tuple(rate_totals)


# --------------------------------------------------------------------------- trimmings


def _context(
    tier: Tier,
    rng: random.Random,
    seller: pools.Company,
    buyer: pools.Company,
    issue_date: dt.date,
    *,
    units: tuple[str, ...],
    rate_totals: tuple[RateTotal, ...],
    total_gross: Decimal,
) -> Context:
    rates_used = {total.rate for total in rate_totals}
    fx_rate = _draw_fx_rate(rng) if tier.currency != "PLN" else None
    return Context(
        seller=seller,
        buyer=buyer,
        issued_at=dt.datetime.combine(issue_date, dt.time(rng.randint(8, 17), rng.randint(0, 59))),
        place=rng.choice(pools.ISSUE_PLACES),
        line_units=units,
        payment_due=issue_date + dt.timedelta(days=rng.choice(_PAYMENT_TERM_DAYS)),
        payment_form=rng.choice(pools.PAYMENT_FORMS),
        bank_name=rng.choice(pools.BANKS),
        annotations=Annotations(
            exempt="zw" in rates_used,
            reverse_charge="oo" in rates_used,
            split_payment=tier.split_payment,
            cash_basis=False,
            self_billing=False,
        ),
        fx_rate=fx_rate,
        fx_date=issue_date - dt.timedelta(days=1) if fx_rate is not None else None,
        vat_in_pln=(
            tuple(round_money(total.vat * fx_rate) for total in rate_totals)
            if fx_rate is not None
            else ()
        ),
        corrected_number=_corrected_number(issue_date, rng) if tier.kind == "KOR" else None,
        corrected_date=issue_date - dt.timedelta(days=rng.randint(14, 90))
        if tier.kind == "KOR"
        else None,
        correction_reason=rng.choice(pools.CORRECTION_REASONS) if tier.kind == "KOR" else None,
        gross_before_correction=round_money(abs(total_gross) * Decimal(rng.randint(3, 9)))
        if tier.kind == "KOR"
        else None,
        order_value=round_money(total_gross * Decimal(rng.randint(3, 6)))
        if tier.kind == "ZAL"
        else None,
    )


def _draw_fx_rate(rng: random.Random) -> Decimal:
    """An NBP mid rate, at the four decimal places the table publishes."""
    return Decimal(rng.randint(41_500, 46_500)) / 10_000


def _random_date(rng: random.Random) -> dt.date:
    span = (_LAST_DAY - _FIRST_DAY).days
    return _FIRST_DAY + dt.timedelta(days=rng.randint(0, span))


def _number(tier: Tier, issue_date: dt.date, rng: random.Random) -> str:
    prefix = {"KOR": "KOR", "ZAL": "ZAL"}.get(tier.kind, rng.choice(("FV", "FA", "F")))
    pattern = rng.choice((
        "{p}/{y}/{m:02d}/{n:04d}", "{p} {n}/{m:02d}/{y}", "{p}-{y}{m:02d}-{n:03d}",
    ))
    return pattern.format(p=prefix, y=issue_date.year, m=issue_date.month, n=rng.randint(1, 999))


def _corrected_number(issue_date: dt.date, rng: random.Random) -> str:
    return f"FV/{issue_date.year}/{rng.randint(1, 12):02d}/{rng.randint(1, 999):04d}"
