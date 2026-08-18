"""`apportion` is what lets a per-rate total and its own line items both be exactly right.

Two invariants pull against each other: the tax on a rate group is levied on the group's net total,
while the same tax is also printed row by row and those rows must sum to it. Rounding each row on
its own does not generally give that sum. These tests pin the two properties the generator relies
on — the parts add up exactly, and no part is more than a grosz from its own rounded share, which
is precisely the tolerance `invariants.lines.vat_matches_rate` allows.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from doc_extract.synth.money import GROSZ, apportion, round_money


def d(value: str) -> Decimal:
    return Decimal(value)


def test_parts_sum_to_the_total_exactly():
    shares = [d("10.005"), d("20.005"), d("30.005")]
    total = d("60.02")
    assert sum(apportion(total, shares)) == total


def test_no_part_drifts_more_than_a_grosz_from_its_own_share():
    """The bound the per-line VAT rule depends on: one grosz is exactly its tolerance."""
    shares = [d("0.004999") for _ in range(40)]
    total = d("0.20")
    for part, share in zip(apportion(total, shares), shares, strict=True):
        assert abs(part - round_money(share)) <= GROSZ


def test_an_already_exact_split_is_left_alone():
    shares = [d("1.00"), d("2.00"), d("3.00")]
    assert apportion(d("6.00"), shares) == (d("1.00"), d("2.00"), d("3.00"))


def test_negative_amounts_apportion_the_same_way():
    """A correction invoice carries negative amounts; nothing about the split may change."""
    shares = [d("-10.005"), d("-20.005")]
    total = d("-30.01")
    parts = apportion(total, shares)
    assert sum(parts) == total
    assert all(part < 0 for part in parts)


def test_every_part_is_two_decimal_places():
    parts = apportion(d("100.00"), [d("33.333"), d("33.333"), d("33.334")])
    assert all(-part.as_tuple().exponent == 2 for part in parts)


def test_a_leftover_larger_than_one_grosz_per_part_is_refused():
    """Silence here would mean the generator quietly emitting amounts that do not reconcile."""
    with pytest.raises(ValueError, match="do not add up"):
        apportion(d("100.00"), [d("1.00"), d("1.00")])


def test_round_money_goes_half_away_from_zero():
    """Half up in both directions, which is what Polish invoicing software does."""
    assert round_money(d("2.345")) == d("2.35")
    assert round_money(d("-2.345")) == d("-2.35")


def test_apportion_is_not_the_invariants_rounding_helper():
    """The generator owns its arithmetic; a shared helper would cancel its own errors.

    If `invariants` and the generator rounded through one function, a wrong rule would round the
    corpus and the check the same way and no test could see it. This asserts the two modules are
    genuinely separate objects, so the duplication stays deliberate rather than drifting into an
    import somebody adds later for tidiness.
    """
    from doc_extract.schema import invariants

    assert invariants._round2 is not round_money


def test_apportion_refuses_a_leftover_that_is_not_whole_grosze():
    """It used to round the step count, do nothing, and return parts that did not sum to the total.

    Every current caller passes two-decimal amounts, so this cannot happen today — which is exactly
    why it deserves an exception rather than trust: the failure it guards against is a corpus whose
    rows quietly do not add up, and this module raises loudly on the neighbouring failure already.
    """
    with pytest.raises(ValueError, match="whole number of grosze"):
        apportion(Decimal("10.005"), [Decimal("5.00"), Decimal("5.00")])
