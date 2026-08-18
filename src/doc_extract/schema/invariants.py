"""Cross-field consistency rules an invoice must satisfy — the project's error detector.

The KSeF FA(3) XSD contains **no assertions**. It is XSD 1.0, so it validates types, enumerations
and cardinality and nothing else: `P_15` is a bare decimal with no stated relationship to the
per-rate totals, and those have none to the line items. Every arithmetic relationship an invoice
obviously satisfies is unenforced by the standard, which is what makes checking it worth doing.

That redundancy is a **label-free correctness signal**. An extractor's output can be checked
against arithmetic the issuer already performed, on any document, including one nobody annotated.
Whether that signal actually predicts extraction error is an empirical question this module exists
to make measurable — it is not assumed here.

**Rules report, they do not raise.** `check` returns violations as data so a failing document can
be routed, explained and counted. Each violation names a stable `rule` id, so per-rule precision
and recall can be tracked over time rather than collapsing into one "invalid" flag.

**Severity is part of the design, not decoration.** `HARD` rules are arithmetic identities that
hold for every well-formed invoice; a violation means something is genuinely wrong. `HEURISTIC`
rules usually hold but have lawful exceptions. Mixing the two would blunt the detector: a
heuristic's false positives would be indistinguishable from a real arithmetic miss. Downstream
metrics are expected to report them separately.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from doc_extract.schema import checksums, vocab
from doc_extract.schema.ksef import Invoice

_CENT = Decimal("0.01")

#: Amounts and per-rate totals are both stored at two decimal places, so their sums are exact.
#: A miss here is a real disagreement, not a rounding artifact.
EXACT = Decimal("0")

#: A rate total's VAT is recomputed the same way the issuer computed it — rate applied to the
#: group's net, rounded to the grosz — so a correct document lands on it exactly. Measured across
#: the corpus, all 192 gold rate totals deviate by 0.00, which is why this is EXACT rather than a
#: grosz: a tolerance here buys no correct document anything and costs the detector every
#: single-grosz error in `P_14_x`, including one carried consistently through into `P_15`.
RATE_VAT_TOLERANCE = EXACT

#: A row's VAT is *not* recomputed the same way. It is apportioned out of the group total so the
#: rows sum to it exactly, which leaves each row within one grosz of its own rounded share — see
#: `synth.money.apportion`, where that bound is proved. 8.2 % of gold rows sit at exactly one
#: grosz, so this tolerance is load-bearing rather than defensive.
LINE_VAT_TOLERANCE = _CENT

#: A line total is `quantity x unit price - discount` rounded to the grosz, while the unit price
#: itself carries eight fractional digits (`TKwotowy2`). Half a grosz is therefore the largest
#: legitimate gap; anything more is not rounding.
LINE_TOLERANCE = Decimal("0.005")

#: A seller may issue an invoice up to 60 days before delivery (art. 106i ust. 7 ustawy o VAT).
#: Beyond that the pairing is suspect — but exceptions exist, hence HEURISTIC.
ISSUE_BEFORE_SALE_DAYS = 60

#: The other direction: an invoice is due by the 15th of the month following the sale (art. 106i
#: ust. 1), so about 45 days is the lawful ceiling. Worth checking separately because the common
#: extraction error is not a late invoice — it is a misread year, which puts the sale a year before
#: the issue and would otherwise pass every rule in this module.
ISSUE_AFTER_SALE_DAYS = 45


class Severity(StrEnum):
    HARD = "hard"
    HEURISTIC = "heuristic"


@dataclass(frozen=True, slots=True)
class Violation:
    """One broken rule, carrying enough context to explain and to aggregate."""

    rule: str
    severity: Severity
    message: str
    fields: tuple[str, ...] = ()
    delta: Decimal | None = None    #: signed miss, for money rules: observed - expected


def _round2(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def _off_by(observed: Decimal, expected: Decimal, tolerance: Decimal) -> Decimal | None:
    """The signed miss when it exceeds tolerance, else None."""
    delta = observed - expected
    return delta if abs(delta) > tolerance else None


# --------------------------------------------------------------------------- totals


def _gross_equals_net_plus_vat(inv: Invoice) -> list[Violation]:
    if not inv.rate_totals:
        return []
    expected = sum((r.net + r.vat for r in inv.rate_totals), Decimal(0))
    delta = _off_by(inv.total_gross, expected, EXACT)
    if delta is None:
        return []
    return [Violation(
        rule="totals.gross_equals_net_plus_vat",
        severity=Severity.HARD,
        message=f"P_15 is {inv.total_gross}, but the rate totals sum to {expected}",
        fields=("total_gross", "rate_totals"),
        delta=delta,
    )]


def _gross_equals_line_sum(inv: Invoice) -> list[Violation]:
    """P_15 against the rows — the third redundancy path, and the one nothing else covers.

    `_gross_equals_net_plus_vat` reads `total_gross` only against `rate_totals`, so an extraction
    that lost the entire item table, or lost the per-rate blocks, or invented a row at a rate the
    totals never mention, comes back from `check()` with nothing at all. Those are precisely the
    failures the `multi_page` tier exists to provoke, which would have left the detector blind in
    the tier aimed at it.

    Exact, like the rate-total rule: rows and the gross are both stored at the grosz, so their sums
    agree or they disagree. It holds on every document of every tier, so the recall it adds costs
    no false positives on correct gold.
    """
    if not inv.lines:
        return []
    amounts = [(line.net, line.vat) for line in inv.lines]
    if any(net is None or vat is None for net, vat in amounts):
        return []  # a simplified row omits amounts; the rule cannot apply
    expected = sum((net + vat for net, vat in amounts), Decimal(0))
    delta = _off_by(inv.total_gross, expected, EXACT)
    if delta is None:
        return []
    return [Violation(
        rule="totals.gross_equals_line_sum",
        severity=Severity.HARD,
        message=(
            f"P_15 is {inv.total_gross}, but its {len(inv.lines)} line(s) sum to {expected}"
        ),
        fields=("total_gross", "lines"),
        delta=delta,
    )]


def _gross_has_support(inv: Invoice) -> list[Violation]:
    """A non-zero P_15 with neither rate totals nor rows behind it — nothing can check it.

    Every other rule here needs two figures to compare. A total standing alone gives them one, so
    an extraction that returned the gross and lost everything else came back indistinguishable from
    a correct document: `check()` was empty because nothing could apply, not because nothing was
    wrong. That is the gap worth reporting — "no rule could run" is itself the finding.

    HEURISTIC, and not merely out of caution. This is a statement about a document being complete,
    not an arithmetic identity, and `UPR` — the faktura uproszczona, Poland's receipt-with-a-NIP
    for small sales — lawfully carries a total and nothing else. Calling that hard would mean the
    detector's false positives were indistinguishable from real arithmetic misses, which is the one
    thing the severity split exists to prevent, so the lawful case is excluded by name.
    """
    if inv.kind == "UPR" or inv.total_gross == 0 or inv.rate_totals or inv.lines:
        return []
    return [Violation(
        rule="totals.gross_has_no_support",
        severity=Severity.HEURISTIC,
        message=(
            f"a {inv.kind} invoice states P_15 of {inv.total_gross} with no rate totals and no "
            "line items, so no arithmetic rule can confirm or contradict it"
        ),
        fields=("total_gross", "rate_totals", "lines"),
    )]


def _rate_codes_unique(inv: Invoice) -> list[Violation]:
    repeated = [code for code, n in Counter(r.rate for r in inv.rate_totals).items() if n > 1]
    return [
        Violation(
            rule="totals.rate_codes_unique",
            severity=Severity.HARD,
            message=f"rate {code!r} appears in more than one P_13/P_14 block",
            fields=("rate_totals",),
        )
        for code in sorted(repeated)
    ]


def _vat_matches_rate(inv: Invoice) -> list[Violation]:
    out = []
    for total in inv.rate_totals:
        expected = _round2(total.net * vocab.RATE_FRACTION[total.rate])
        delta = _off_by(total.vat, expected, RATE_VAT_TOLERANCE)
        if delta is not None:
            out.append(Violation(
                rule="totals.vat_matches_rate",
                severity=Severity.HARD,
                message=(
                    f"rate {total.rate!r}: VAT is {total.vat}, but {total.net} at this rate "
                    f"gives {expected}"
                ),
                fields=("rate_totals",),
                delta=delta,
            ))
    return out


def _lines_match_rate_totals(inv: Invoice) -> list[Violation]:
    """Lines and rate totals are both stored at the grosz, so their sums must agree exactly."""
    if not inv.lines or not inv.rate_totals:
        return []
    by_rate: dict[str, list] = defaultdict(list)
    for line in inv.lines:
        if line.vat_rate is not None:
            by_rate[line.vat_rate].append(line)

    out = []
    for total in inv.rate_totals:
        lines = by_rate.get(total.rate)
        if not lines:
            continue  # the invoice states a rate total with no line carrying it — a shape gap
        for attr, stated in (("net", total.net), ("vat", total.vat)):
            values = [getattr(line, attr) for line in lines]
            if any(v is None for v in values):
                continue  # simplified rows omit amounts; the rule cannot apply
            summed = sum(values, Decimal(0))
            delta = _off_by(stated, summed, EXACT)
            if delta is not None:
                out.append(Violation(
                    rule=f"lines.sum_matches_rate_{attr}",
                    severity=Severity.HARD,
                    message=(
                        f"rate {total.rate!r}: stated {attr} {stated}, but its "
                        f"{len(lines)} line(s) sum to {summed}"
                    ),
                    fields=("lines", "rate_totals"),
                    delta=delta,
                ))
    return out


def _amounts_signed_correctly(inv: Invoice) -> list[Violation]:
    """Only a correction may carry negative amounts; anything else is a sign error.

    Rows are checked as well as totals. A single row whose sign was misread is invisible in the
    totals as soon as another row offsets it — the document still adds up, and every summing rule
    here passes — so reading only the totals would leave the error to be found by the one thing
    that cannot see it.
    """
    if inv.is_correction:
        return []
    negatives = [t.rate for t in inv.rate_totals if t.net < 0 or t.vat < 0]
    out = []
    out += [
        Violation(
            rule="totals.non_correction_amounts_non_negative",
            severity=Severity.HARD,
            message=(
                f"{inv.kind} invoice has a negative amount on line {line.line_no}"
            ),
            fields=("lines",),
        )
        for line in inv.lines
        if (line.net is not None and line.net < 0)
        or (line.vat is not None and line.vat < 0)
        or (line.quantity is not None and line.quantity < 0)
    ]
    if inv.total_gross < 0:
        out.append(Violation(
            rule="totals.non_correction_amounts_non_negative",
            severity=Severity.HARD,
            message=f"{inv.kind} invoice has a negative P_15 of {inv.total_gross}",
            fields=("total_gross",),
            delta=inv.total_gross,
        ))
    out += [
        Violation(
            rule="totals.non_correction_amounts_non_negative",
            severity=Severity.HARD,
            message=f"{inv.kind} invoice has a negative amount at rate {rate!r}",
            fields=("rate_totals",),
        )
        for rate in negatives
    ]
    return out


# --------------------------------------------------------------------------- lines


def _line_numbers_unique(inv: Invoice) -> list[Violation]:
    repeated = [n for n, c in Counter(line.line_no for line in inv.lines).items() if c > 1]
    return [
        Violation(
            rule="lines.numbers_unique",
            severity=Severity.HARD,
            message=f"line number {n} is used more than once",
            fields=("lines",),
        )
        for n in sorted(repeated)
    ]


def _line_net_matches_quantity(inv: Invoice) -> list[Violation]:
    out = []
    for line in inv.lines:
        if line.net is None or line.quantity is None or line.unit_price_net is None:
            continue
        expected = line.quantity * line.unit_price_net - (line.discount or Decimal(0))
        delta = _off_by(line.net, expected, LINE_TOLERANCE)
        if delta is not None:
            out.append(Violation(
                rule="lines.net_matches_quantity_times_price",
                severity=Severity.HARD,
                message=(
                    f"line {line.line_no}: net {line.net}, but "
                    f"{line.quantity} x {line.unit_price_net} gives {expected}"
                ),
                fields=("lines",),
                delta=delta,
            ))
    return out


def _line_vat_matches_rate(inv: Invoice) -> list[Violation]:
    out = []
    for line in inv.lines:
        if line.net is None or line.vat is None or line.vat_rate is None:
            continue
        expected = _round2(line.net * vocab.RATE_FRACTION[line.vat_rate])
        delta = _off_by(line.vat, expected, LINE_VAT_TOLERANCE)
        if delta is not None:
            out.append(Violation(
                rule="lines.vat_matches_rate",
                severity=Severity.HARD,
                message=(
                    f"line {line.line_no} at rate {line.vat_rate!r}: VAT {line.vat}, "
                    f"but {line.net} gives {expected}"
                ),
                fields=("lines",),
                delta=delta,
            ))
    return out


# --------------------------------------------------------------------------- identifiers


def _identifier_checksums(inv: Invoice) -> list[Violation]:
    out = []
    for role, party in (("seller", inv.seller), ("buyer", inv.buyer)):
        if party.nip is not None and not checksums.is_valid_nip(party.nip):
            out.append(Violation(
                rule="identifiers.nip_checksum",
                severity=Severity.HARD,
                message=f"{role} NIP {party.nip!r} fails its check digit",
                fields=(f"{role}.nip",),
            ))
    if inv.payment_account is not None and not checksums.is_valid_iban(
        inv.payment_account, country="PL"
    ):
        out.append(Violation(
            rule="identifiers.iban_checksum",
            severity=Severity.HARD,
            message=f"payment account {inv.payment_account!r} fails the IBAN mod-97 check",
            fields=("payment_account",),
        ))
    return out


# --------------------------------------------------------------------------- dates


def _issue_near_sale(inv: Invoice) -> list[Violation]:
    """Heuristic: an invoice and the sale it documents sit close together, in either direction.

    Checking only one direction left the more common extraction error invisible. A misread year —
    `2025-08-05` for `2026-08-05` — puts the sale 365 days *before* the issue, where the old
    comparison went negative and the rule stayed silent. Both bounds are lawful ceilings rather
    than round numbers, and both are HEURISTIC because a late invoice is irregular, not impossible.
    """
    if inv.sale_date is None:
        return []
    days_early = (inv.sale_date - inv.issue_date).days
    if days_early > ISSUE_BEFORE_SALE_DAYS:
        return [Violation(
            rule="dates.issue_near_sale",
            severity=Severity.HEURISTIC,
            message=(
                f"issued {inv.issue_date}, {days_early} days before the sale date {inv.sale_date} "
                f"(art. 106i ust. 7 allows {ISSUE_BEFORE_SALE_DAYS})"
            ),
            fields=("issue_date", "sale_date"),
        )]
    if -days_early > ISSUE_AFTER_SALE_DAYS:
        return [Violation(
            rule="dates.issue_follows_sale",
            severity=Severity.HEURISTIC,
            message=(
                f"issued {inv.issue_date}, {-days_early} days after the sale date {inv.sale_date} "
                f"(art. 106i ust. 1 allows about {ISSUE_AFTER_SALE_DAYS})"
            ),
            fields=("issue_date", "sale_date"),
        )]
    return []


_RULES = (
    _gross_equals_net_plus_vat,
    _gross_equals_line_sum,
    _gross_has_support,
    _rate_codes_unique,
    _vat_matches_rate,
    _lines_match_rate_totals,
    _amounts_signed_correctly,
    _line_numbers_unique,
    _line_net_matches_quantity,
    _line_vat_matches_rate,
    _identifier_checksums,
    _issue_near_sale,
)


def check(invoice: Invoice) -> tuple[Violation, ...]:
    """Every rule this invoice breaks, once each, in a stable order.

    "Nothing detectable" is not "correct": a rule whose inputs are absent cannot fire, and an
    extraction wrong in a way arithmetic cannot see passes silently. Measuring that gap is what
    the detector study exists for.

    Identical violations are collapsed. A `Violation` carries its own values in `message` and
    `delta`, so two that compare equal describe the same disagreement about the same figures —
    which is what an invoice repeating a rate code produces, since every rule reading `rate_totals`
    then walks the same block twice. Two genuinely separate misses never collide, because each
    names its own line or rate. Leaving the copies in would double whatever per-rule precision and
    recall M5 reports, for the documents most likely to be malformed in the first place.
    """
    seen: set[Violation] = set()
    out: list[Violation] = []
    for rule in _RULES:
        for violation in rule(invoice):
            if violation not in seen:
                seen.add(violation)
                out.append(violation)
    return tuple(out)


def hard_violations(invoice: Invoice) -> tuple[Violation, ...]:
    """Only the arithmetic identities — the interpretable half of the signal."""
    return tuple(v for v in check(invoice) if v.severity is Severity.HARD)
