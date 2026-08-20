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

**The ten kinds are chosen to span the detector's blind spot, not to be uniformly detectable.**
Five break a hard arithmetic identity and should be caught: a transposed total, a cent on a VAT
figure, a swapped net and VAT, a dropped row, a transposed row net. Two break a check digit. One
breaks a **heuristic** rule and no hard one. Two break nothing an invariant can see — a shifted sale
date and a truncated buyer name — and the whole value of the study is in how many of those slip
through. A corruption set that only contained detectable errors would report a recall of 1.0 and
would have measured its own construction.

`CAUGHT_BY` states, per kind, which severity is expected to notice it, and that is what makes the
per-kind table readable at *both* severities: a transposed total is not a failure of the heuristic
half, and a misread year is not a failure of the arithmetic half. Deriving `INVISIBLE_KINDS` from
that one mapping keeps the claim in a single place.

`year_misread` exists because the heuristic rules had **never fired on any run**, which the
project's own metric rules call broken rather than stable — a rate identical across every variant
measures nothing. It is written to what the rule it exercises already describes in prose:
`dates.issue_near_sale` names a misread year (`2025-08-05` for `2026-08-05`) as the reading error it
was widened to catch. Writing the corruption to that description rather than to the code means a
rule that stopped matching its own docstring would show up as a recall of zero.

**A corruption may not remove a field a later corruption records having changed.** The third
heuristic rule, `totals.gross_has_no_support`, wants an extraction that kept the gross and lost
everything behind it — but emptying `lines` here would erase the row a `line_transposed` injected
one line earlier had already been recorded against, and the prediction file would then claim an
error against a field that is no longer in the document. That scenario is a whole degenerate
extraction rather than one slipped field, so it is a **baseline** (`baselines.stripped`) and not a
kind: every document, honestly labelled, and no interaction with anything here.

Nothing here is random about *whether* the corpus is corrupted: the rate is a parameter, the seed
comes from the document, and re-running the baseline produces the identical errors.
"""

from __future__ import annotations

import datetime as dt
import random
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from doc_extract.schema.invariants import Severity
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


def _sale_year_misread(invoice: Invoice, rng: random.Random) -> tuple[Invoice, Injection] | None:
    """The sale date's year off by one — a whole year wrong, and every hard rule silent.

    `2025-08-05` for `2026-08-05` is the error `dates.issue_near_sale` was widened to catch, and it
    is the one date error a reader would call serious: `date_shifted` moves the day inside the
    lawful window and is genuinely undetectable, while a wrong year puts the sale hundreds of days
    from the invoice that documents it. Nothing arithmetic touches a date, so the only rule that can
    see this is the heuristic one — which is exactly why it is here.

    A leap day cannot survive the shift, so it is moved rather than dropped: `Decimal`-style
    exactness is not the point here, and refusing to corrupt one document in 1461 would leave a
    silent hole in the support column.
    """
    sale = invoice.sale_date
    if sale is None:
        return None
    years = rng.choice((-1, 1))
    day = 28 if (sale.month, sale.day) == (2, 29) else sale.day
    changed = sale.replace(year=sale.year + years, day=day)
    return (
        _replace(invoice, sale_date=changed),
        Injection("year_misread", "sale_date", sale.isoformat(), changed.isoformat()),
    )


#: In a fixed order, so the same seed and the same rate give the same document every time. Two
#: corruptions can fire on one document, which is realistic and is also why the order is fixed: a
#: dropped line changes what a later corruption can pick.
#:
#: `year_misread` is placed **before** `date_shifted` deliberately. They are the one pair that
#: writes the same field, so at most one can be recorded on a document, and the order decides which
#: — the later one is discarded rather than allowed to falsify the earlier one's note. The heuristic
#: half of the rule set owns exactly one kind and `year_misread` is it, while `date_shifted` is a
#: control whose whole job is to be missed and whose population `name_truncated` already supplies.
#: Losing a firing of the control costs a redundant zero; losing a firing of `year_misread` costs
#: the only rate the heuristic half has.
CORRUPTIONS: tuple[tuple[str, Corruption], ...] = (
    ("total_transposed", _total_transposed),
    ("vat_cent", _vat_off_by_a_cent),
    ("rate_swapped", _rate_halves_swapped),
    ("line_dropped", _line_dropped),
    ("line_transposed", _line_transposed),
    ("nip_digit", _nip_digit),
    ("account_digit", _account_digit),
    ("year_misread", _sale_year_misread),
    ("date_shifted", _sale_date_shifted),
    ("name_truncated", _buyer_name_truncated),
)

KINDS: tuple[str, ...] = tuple(name for name, _ in CORRUPTIONS)

#: Which severity is expected to notice each kind, or `None` for the ones nothing can see. This is
#: the single place the claim is made: `INVISIBLE_KINDS` is derived from it, the per-kind table
#: reads it to label a row at the severity being reported, and M5 asserts it against the rule set
#: rather than trusting it. A kind absent from a study's own severity is not that severity's
#: failure — a transposed total is not something a heuristic was ever going to catch.
CAUGHT_BY: dict[str, Severity | None] = {
    "total_transposed": Severity.HARD,
    "vat_cent": Severity.HARD,
    "rate_swapped": Severity.HARD,
    "line_dropped": Severity.HARD,
    "line_transposed": Severity.HARD,
    "nip_digit": Severity.HARD,
    "account_digit": Severity.HARD,
    "date_shifted": None,
    "year_misread": Severity.HEURISTIC,
    "name_truncated": None,
}

#: The kinds no invariant can see: a date shift inside the lawful window and a shortened name.
INVISIBLE_KINDS: frozenset[str] = frozenset(
    kind for kind, severity in CAUGHT_BY.items() if severity is None
)


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
        changed, injection = applied
        if any(_collides(injection.field, recorded.field) for recorded in injections):
            #: A second corruption of a field an earlier one already recorded is dropped, because
            #: the record would then be false: the earlier note's `after` is not what the document
            #: says any more, and the prediction file would credit a rule's catch to a change the
            #: document no longer carries. Discarded *after* calling, so the RNG stream stays the
            #: one the ordering describes.
            continue
        invoice = changed
        injections.append(injection)
    return invoice, tuple(injections)


def _collides(field: str, recorded: str) -> bool:
    """Whether writing `field` would falsify a note already recorded against `recorded`.

    Equality is not enough, because a field path and its parent are different strings and the same
    value. `rate_swapped` names `rate_totals[zw]` and `vat_cent` names `rate_totals[zw].vat`: the
    swap rewrites the block the cent was recorded against, and the note's `after` then describes a
    figure the document does not carry. The first version of this guard compared the two strings and
    let exactly that through — invisible on the committed runs, where `DEFAULT_RATE` never put both
    kinds on one document, and reachable from the CLI's own `--rate`.

    Containment in either direction, because neither is privileged: a parent written after a child
    erases the child's record, and a child written after a parent contradicts it.
    """
    return (
        field == recorded
        or field.startswith(f"{recorded}.")
        or recorded.startswith(f"{field}.")
    )


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
