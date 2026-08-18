"""Decimal arithmetic owned by the corpus generator — deliberately not shared with anything else.

If the generator and the scorer rounded through one helper, a wrong rounding rule would cancel:
the corpus would be rounded exactly the way the metric expects it to be, and no test could see the
error. The same argument applies to `schema.invariants`, which has its own `_round2`. Three copies
of `quantize(ROUND_HALF_UP)` is the price of keeping the three able to disagree.

`apportion` is the only non-trivial piece here, and it exists because two invariants pull against
each other. VAT is levied on a rate group's total net (`P_14_x` against `P_13_x`), but an invoice
also prints VAT per line (`P_11Vat`), and those lines must sum to the group total exactly.
Rounding each line independently does not generally give that sum. Apportioning fixes it, and the
bound it guarantees is what keeps the per-line rule satisfiable — see `apportion` for the proof.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

#: The smallest unit a printed amount can carry. Every `TKwotowy` in FA(3) has two decimals.
GROSZ = Decimal("0.01")


def round_money(value: Decimal) -> Decimal:
    """Two decimal places, half away from zero — the rule Polish invoicing software applies."""
    return value.quantize(GROSZ, rounding=ROUND_HALF_UP)


def apportion(total: Decimal, shares: Sequence[Decimal]) -> tuple[Decimal, ...]:
    """Split `total` across `shares`, so the parts sum to it exactly and each stays near its share.

    `shares` are the *unrounded* amounts each part is entitled to — typically `line_net x rate`.
    Each part starts as its own rounded share, and the leftover grosze are then handed out one per
    part, to whichever parts were rounded furthest in the wrong direction.

    **Why one grosz per part is always enough, and why it matters.** Each rounded share is within
    half a grosz of its exact value, so `n` parts drift from their sum by at most `n/2` grosze; the
    target itself is a rounded figure, contributing at most another half. The leftover is therefore
    never more than `(n + 1) / 2` grosze — never more than `n` for any `n ≥ 1` — so no part is ever
    adjusted twice. That bound is the point: it means every part lands within a single grosz of
    `round_money(share)`, which is exactly the tolerance `invariants.lines.vat_matches_rate` allows.
    Apportioning any more loosely would produce a corpus whose own gold breaks a hard rule.

    Signs are handled by the ordering rather than by special cases, so a correction invoice with
    negative amounts apportions the same way an ordinary one does.
    """
    parts = [round_money(share) for share in shares]
    leftover = total - sum(parts, Decimal(0))
    if leftover == 0:
        return tuple(parts)

    grosze = abs(leftover) / GROSZ
    if grosze != grosze.to_integral_value():
        #: `int(...to_integral_value())` rounds, so a leftover that is not a whole number of grosze
        #: would quantise to zero steps, the loop below would do nothing, and the parts would be
        #: returned silently not summing to `total`. Every caller passes two-decimal inputs, so
        #: reaching this means an assumption broke — which is worth a message, not a wrong corpus.
        raise ValueError(
            f"cannot apportion {total} across {len(parts)} part(s): a leftover of {leftover} is "
            "not a whole number of grosze, so no assignment of grosze can close it"
        )

    steps = int(grosze)
    if steps > len(parts):
        raise ValueError(
            f"cannot apportion {total} across {len(parts)} part(s): {steps} grosz left over, "
            "which means `shares` do not add up to `total`"
        )

    direction = GROSZ if leftover > 0 else -GROSZ
    #: Adjust the parts that were rounded furthest against the direction we need to move.
    towards = 1 if leftover > 0 else -1
    order = sorted(
        range(len(parts)), key=lambda i: (shares[i] - parts[i]) * towards, reverse=True
    )
    for index in order[:steps]:
        parts[index] += direction
    return tuple(parts)


def total_of(amounts: Sequence[Decimal]) -> Decimal:
    """Sum at two decimal places. Both operands are already exact, so this cannot round."""
    return sum(amounts, Decimal(0))
