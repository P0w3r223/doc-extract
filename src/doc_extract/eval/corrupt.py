"""Known errors, injected on purpose, so that M5 can ask whether the invariants notice.

The detector study has a chicken-and-egg problem: to measure whether "the arithmetic holds" predicts
"the fields are right", you need documents whose fields are *wrong* in ways you already know. Until
a model has been run there are none, and even afterwards a model's mistakes are unlabelled — you can
score them, but you cannot choose them, and a detector measured only on whatever a model happened to
get wrong is measured on a sample nobody controls.

So this module makes them. Each corruption is one plausible reading error applied to one field of a
gold invoice, with a seeded RNG, and every one that fires is **recorded** on the prediction. M5 can
then cross two columns it did not have to infer: what was actually broken, and what `invariants`
said about it.

**The nine kinds are chosen to span the detector's blind spot, not to be uniformly detectable.**
Five break a hard arithmetic identity and should be caught: a transposed total, a cent on a VAT
figure, a swapped net and VAT, a dropped row, a transposed row net. Two break a check digit. Two
break nothing an invariant can see — a shifted sale date and a truncated buyer name — and the whole
value of the study is in how many of those slip through. A corruption set that only contained
detectable errors would report a recall of 1.0 and would have measured its own construction.

Nothing here is random about *whether* the corpus is corrupted: the rate is a parameter, the seed
comes from the document, and re-running the baseline produces the identical errors.
"""

from __future__ import annotations

import datetime as dt
import random
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from doc_extract.schema.ksef import Invoice, LineItem, Party, RateTotal

#: How often each kind fires on a given document, independently of the others.
DEFAULT_RATE = 0.1

#: A day shift large enough to matter to a reader and small enough that no hard rule sees it.
_DATE_SHIFT_DAYS = (-9, -5, -3, 3, 5, 9)

_CENT = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Injection:
    """One corruption that fired: what was done, to which field, and to what value.

    The `note` format is `"<kind> <field>: <before> -> <after>"` and is what lands in the prediction
    file. Flat text rather than a nested object because a reader greps prediction files, and the
    kind is the first token for exactly that reason.
    """

    kind: str
    field: str
    before: str
    after: str

    @property
    def note(self) -> str:
        return f"{self.kind} {self.field}: {self.before} -> {self.after}"


#: One corruption: the invoice it is given, the RNG, and either a changed invoice with the record of
#: what changed, or `None` when this document offers nothing to break.
Corruption = Callable[[Invoice, random.Random], tuple[Invoice, Injection] | None]


def _total_transposed(invoice: Invoice, rng: random.Random) -> tuple[Invoice, Injection] | None:
    """Two adjacent digits of the gross total swapped — the classic transcription slip."""
    changed = _transpose(invoice.total_gross, rng)
    if changed is None:
        return None
    return (
        _replace(invoice, total_gross=changed),
        Injection("total_transposed", "total_gross", _plain(invoice.total_gross), _plain(changed)),
    )


def _vat_off_by_a_cent(invoice: Invoice, rng: random.Random) -> tuple[Invoice, Injection] | None:
    """One grosz on one rate block's VAT: the smallest error a hard rule is required to catch."""
    if not invoice.rate_totals:
        return None
    index = rng.randrange(len(invoice.rate_totals))
    total = invoice.rate_totals[index]
    changed = total.vat + (_CENT if rng.random() < 0.5 else -_CENT)
    return (
        _replace(invoice, rate_totals=_swap(invoice.rate_totals, index, _with(total, vat=changed))),
        Injection("vat_cent", f"rate_totals[{total.rate}].vat", _plain(total.vat), _plain(changed)),
    )


def _rate_halves_swapped(invoice: Invoice, rng: random.Random) -> tuple[Invoice, Injection] | None:
    """Net and VAT read out of each other's column — a real failure of a mis-parsed table."""
    candidates = [
        index for index, total in enumerate(invoice.rate_totals) if total.net != total.vat
    ]
    if not candidates:
        return None
    index = rng.choice(candidates)
    total = invoice.rate_totals[index]
    swapped = _with(total, net=total.vat, vat=total.net)
    return (
        _replace(invoice, rate_totals=_swap(invoice.rate_totals, index, swapped)),
        Injection(
            "rate_swapped", f"rate_totals[{total.rate}]",
            f"{_plain(total.net)}/{_plain(total.vat)}",
            f"{_plain(swapped.net)}/{_plain(swapped.vat)}",
        ),
    )


def _line_dropped(invoice: Invoice, rng: random.Random) -> tuple[Invoice, Injection] | None:
    """A row missed entirely — what a page break or a tall table does to a careless reader."""
    if len(invoice.lines) < 2:
        return None
    index = rng.randrange(len(invoice.lines))
    dropped = invoice.lines[index]
    remaining = invoice.lines[:index] + invoice.lines[index + 1:]
    return (
        _replace(invoice, lines=remaining),
        Injection("line_dropped", f"lines[{dropped.line_no}]", _plain(dropped.net), "absent"),
    )


def _line_transposed(invoice: Invoice, rng: random.Random) -> tuple[Invoice, Injection] | None:
    """A row's net value misread, leaving the summary block it belongs to intact."""
    candidates = [line for line in invoice.lines if line.net is not None]
    if not candidates:
        return None
    line = rng.choice(candidates)
    net = line.net
    changed = None if net is None else _transpose(net, rng)
    if net is None or changed is None:
        return None
    index = invoice.lines.index(line)
    return (
        _replace(invoice, lines=_swap(invoice.lines, index, _with(line, net=changed))),
        Injection("line_transposed", f"lines[{line.line_no}].net", _plain(net), _plain(changed)),
    )


def _nip_digit(invoice: Invoice, rng: random.Random) -> tuple[Invoice, Injection] | None:
    """One digit of the seller's NIP — the error a check digit exists to catch."""
    nip = invoice.seller.nip
    if not nip or not nip.isdigit():
        return None
    changed = _change_digit(nip, rng)
    return (
        _replace(invoice, seller=_with(invoice.seller, nip=changed)),
        Injection("nip_digit", "seller.nip", nip, changed),
    )


def _account_digit(invoice: Invoice, rng: random.Random) -> tuple[Invoice, Injection] | None:
    """One digit of the bank account — caught by mod-97, and expensive in the real world."""
    account = invoice.payment_account
    if not account or not account[-1:].isdigit():
        return None
    changed = _change_digit(account, rng)
    return (
        _replace(invoice, payment_account=changed),
        Injection("account_digit", "payment_account", account, changed),
    )


def _sale_date_shifted(invoice: Invoice, rng: random.Random) -> tuple[Invoice, Injection] | None:
    """A wrong date that no arithmetic can see. One of the three the study exists to count."""
    if invoice.sale_date is None:
        return None
    changed = invoice.sale_date + dt.timedelta(days=rng.choice(_DATE_SHIFT_DAYS))
    return (
        _replace(invoice, sale_date=changed),
        Injection("date_shifted", "sale_date", invoice.sale_date.isoformat(), changed.isoformat()),
    )


def _buyer_name_truncated(invoice: Invoice, rng: random.Random) -> tuple[Invoice, Injection] | None:
    """The buyer's legal form dropped: invisible to every invariant, and wrong on an invoice."""
    name = invoice.buyer.name
    if " " not in name.strip():
        return None
    changed = name.rsplit(" ", 1)[0].strip()
    if not changed:
        return None
    return (
        _replace(invoice, buyer=_with(invoice.buyer, name=changed)),
        Injection("name_truncated", "buyer.name", name, changed),
    )


#: In a fixed order, so the same seed and the same rate give the same document every time. Two
#: corruptions can fire on one document, which is realistic and is also why the order is fixed: a
#: dropped line changes what a later corruption can pick.
CORRUPTIONS: tuple[tuple[str, Corruption], ...] = (
    ("total_transposed", _total_transposed),
    ("vat_cent", _vat_off_by_a_cent),
    ("rate_swapped", _rate_halves_swapped),
    ("line_dropped", _line_dropped),
    ("line_transposed", _line_transposed),
    ("nip_digit", _nip_digit),
    ("account_digit", _account_digit),
    ("date_shifted", _sale_date_shifted),
    ("name_truncated", _buyer_name_truncated),
)

KINDS: tuple[str, ...] = tuple(name for name, _ in CORRUPTIONS)

#: The kinds no invariant can see. Named here rather than in M5, because the claim belongs with the
#: corruptions it describes: a date shift inside the lawful window, a shortened name, and — once
#: `invariants` gains no rule for them — nothing else. M5 asserts this against the rule set rather
#: than trusting it.
INVISIBLE_KINDS: frozenset[str] = frozenset({"date_shifted", "name_truncated"})


def corrupt(
    invoice: Invoice, rng: random.Random, *, rate: float = DEFAULT_RATE
) -> tuple[Invoice, tuple[Injection, ...]]:
    """Each corruption fires independently with probability `rate`; the survivors are recorded.

    A rate of 0 returns the invoice unchanged and no injections, which is the oracle — so B0 and B3
    differ by one number rather than by a code path, and the scorer cannot be told which it is
    looking at.
    """
    injections: list[Injection] = []
    for _, corruption in CORRUPTIONS:
        if rng.random() >= rate:
            continue
        applied = corruption(invoice, rng)
        if applied is None:
            continue
        invoice, injection = applied
        injections.append(injection)
    return invoice, tuple(injections)


# --------------------------------------------------------------------------- small surgery


def _replace(invoice: Invoice, **changes: object) -> Invoice:
    """A changed copy that is re-validated rather than patched in place.

    `model_copy(update=...)` would skip validation, and a corruption that produced an invoice the
    schema rejects would then be discovered by the pipeline instead of here. Constructing anew keeps
    every corruption inside what `Invoice` admits — which is the point: these are *reading* errors,
    not malformed documents.
    """
    return Invoice(**{**invoice.model_dump(), **changes})


def _with[Part: (LineItem, Party, RateTotal)](model: Part, **changes: object) -> Part:
    return type(model)(**{**model.model_dump(), **changes})


def _swap[Part](items: tuple[Part, ...], index: int, replacement: Part) -> tuple[Part, ...]:
    return (*items[:index], replacement, *items[index + 1:])


def _transpose(value: Decimal, rng: random.Random) -> Decimal | None:
    """Two adjacent digits swapped, keeping the sign and the number of decimal places.

    Adjacent *in the printed text* and never across the decimal point: `6013.94` becomes `6031.94`,
    not `6019.34`. A swap that jumped the separator would change the magnitude by orders and would
    be caught by eye, which is not the error worth studying.
    """
    text = format(abs(value), "f")
    pairs = [
        index for index in range(len(text) - 1)
        if text[index].isdigit() and text[index + 1].isdigit() and text[index] != text[index + 1]
    ]
    if not pairs:
        return None
    index = rng.choice(pairs)
    characters = list(text)
    characters[index], characters[index + 1] = characters[index + 1], characters[index]
    changed = Decimal("".join(characters))
    return -changed if value < 0 else changed


def _change_digit(text: str, rng: random.Random) -> str:
    positions = [index for index, character in enumerate(text) if character.isdigit()]
    index = rng.choice(positions)
    replacement = rng.choice([digit for digit in "0123456789" if digit != text[index]])
    return text[:index] + replacement + text[index + 1:]


def _plain(value: Decimal) -> str:
    return format(value, "f")
