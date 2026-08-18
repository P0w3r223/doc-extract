"""Every invariant must catch its own violation — and stay quiet on a coherent invoice.

Note that the rules **interlock by design**: one wrong number usually lights up several of them
(a mistyped rate total breaks both `totals.vat_matches_rate` and `lines.sum_matches_rate_vat`).
That is why violations carry a stable `rule` id rather than collapsing into one "invalid" flag,
and why these tests assert a rule is *among* the violations where isolation is not achievable.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from conftest import VALID_IBAN, d, totals_only
from doc_extract.schema.invariants import Severity, check, hard_violations
from doc_extract.schema.ksef import LineItem, Party, RateTotal


def rules(invoice) -> set[str]:
    return {v.rule for v in check(invoice)}


def test_coherent_invoice_has_no_violations(invoice):
    assert check(invoice) == ()


def test_gross_must_equal_net_plus_vat(invoice):
    broken = invoice.model_copy(update={"total_gross": d("400.00")})
    fired = [v for v in check(broken) if v.rule == "totals.gross_equals_net_plus_vat"]
    assert len(fired) == 1
    assert fired[0].severity is Severity.HARD
    assert fired[0].delta == d("60.10")  # 400.00 - 339.90, signed toward the observed value


def test_gross_is_exact_not_tolerant(invoice):
    """A single grosz is a real disagreement: both sides are stored at two decimal places."""
    assert "totals.gross_equals_net_plus_vat" in rules(
        invoice.model_copy(update={"total_gross": d("339.91")})
    )


def test_vat_must_match_its_rate():
    # 100.00 at 23 % is 23.00, not 20.00; the gross still reconciles, so only the rate rule fires.
    assert rules(totals_only(net="100.00", vat="20.00", gross="120.00")) == {
        "totals.vat_matches_rate"
    }


def test_a_single_grosz_in_a_rate_total_is_a_disagreement_not_a_rounding_step():
    """The issuer's own computation is reproduced exactly here, so there is nothing to tolerate.

    A tolerance would buy no correct document anything — every one of the corpus's rate totals
    lands on the recomputed value exactly — while hiding a one-grosz error in `P_14_x`, including
    one carried straight through into a `P_15` that then reconciles against it.
    """
    assert "totals.vat_matches_rate" in rules(
        totals_only(net="100.00", vat="23.01", gross="123.01")
    )
    assert rules(totals_only(net="100.00", vat="23.00", gross="123.00")) == set()


def test_a_line_still_tolerates_the_grosz_apportioning_can_move_it(invoice):
    """Rows are apportioned, not recomputed, so one grosz of drift is the design rather than a bug.

    `money.apportion` guarantees each row lands within a grosz of its own rounded share, which is
    what lets the rows sum to their group total exactly. Tightening this the way the rate-total
    rule was tightened would make the generator's own gold break a hard rule.
    """
    first, *rest = invoice.lines
    nudged = first.model_copy(update={"vat": first.vat + d("0.01")})
    off_by_one = invoice.model_copy(update={"lines": (nudged, *rest)})
    assert "lines.vat_matches_rate" not in rules(off_by_one)

    nudged_twice = first.model_copy(update={"vat": first.vat + d("0.02")})
    assert "lines.vat_matches_rate" in rules(
        invoice.model_copy(update={"lines": (nudged_twice, *rest)})
    )


def test_untaxed_rate_expects_zero_vat():
    assert rules(totals_only(net="100.00", vat="0.00", gross="100.00", rate="zw")) == set()
    assert "totals.vat_matches_rate" in rules(
        totals_only(net="100.00", vat="5.00", gross="105.00", rate="zw")
    )


def test_duplicate_rate_block_is_caught(invoice):
    doubled = (*invoice.rate_totals, RateTotal(rate="23", net=d("0.00"), vat=d("0.00")))
    assert "totals.rate_codes_unique" in rules(invoice.model_copy(update={"rate_totals": doubled}))


def test_lines_must_sum_to_their_rate_total(invoice):
    # Understate the 23 % net by 10.00 and keep the gross consistent with the stated totals,
    # so the line-sum rule is what fires rather than the gross rule.
    totals = (RateTotal(rate="23", net=d("240.00"), vat=d("55.20")), invoice.rate_totals[1])
    broken = invoice.model_copy(
        update={"rate_totals": totals, "total_gross": d("327.60")}
    )
    fired = rules(broken)
    assert "lines.sum_matches_rate_net" in fired
    assert "lines.sum_matches_rate_vat" in fired
    assert "totals.gross_equals_net_plus_vat" not in fired


def test_line_net_must_match_quantity_times_price(invoice):
    # 2 x 100.00 is 200.00, not 250.00. Keep every total consistent with the *stated* line net,
    # so only the quantity rule fires.
    lines = (
        invoice.lines[0].model_copy(update={"net": d("250.00"), "vat": d("57.50")}),
        invoice.lines[1],
        invoice.lines[2],
    )
    totals = (RateTotal(rate="23", net=d("300.00"), vat=d("69.00")), invoice.rate_totals[1])
    broken = invoice.model_copy(
        update={"lines": lines, "rate_totals": totals, "total_gross": d("401.40")}
    )
    assert rules(broken) == {"lines.net_matches_quantity_times_price"}


def test_line_net_tolerates_half_a_grosz():
    """`P_9A` carries eight decimals while totals carry two, so sub-grosz gaps are lawful."""
    base = totals_only(net="0.00", vat="0.00", gross="0.00")
    line = LineItem(line_no=1, quantity=d("3"), unit_price_net=d("0.33333333"),
                    net=d("1.00"), vat=d("0.23"), vat_rate="23")
    within = base.model_copy(update={"lines": (line,), "rate_totals": ()})
    assert "lines.net_matches_quantity_times_price" not in rules(within)

    far = line.model_copy(update={"net": d("1.02")})
    beyond = base.model_copy(update={"lines": (far,), "rate_totals": ()})
    assert "lines.net_matches_quantity_times_price" in rules(beyond)


def test_line_vat_must_match_its_rate(invoice):
    lines = (invoice.lines[0].model_copy(update={"vat": d("40.00")}), *invoice.lines[1:])
    assert "lines.vat_matches_rate" in rules(invoice.model_copy(update={"lines": lines}))


def test_duplicate_line_number_is_caught(invoice):
    lines = (*invoice.lines, invoice.lines[0])
    assert "lines.numbers_unique" in rules(invoice.model_copy(update={"lines": lines}))


def test_negative_amounts_are_allowed_only_on_a_correction(invoice):
    negative = invoice.model_copy(update={"total_gross": d("-339.90")})
    assert "totals.non_correction_amounts_non_negative" in rules(negative)

    correction = negative.model_copy(update={"kind": "KOR"})
    assert "totals.non_correction_amounts_non_negative" not in rules(correction)


def test_bad_nip_check_digit_is_caught(invoice):
    broken = invoice.model_copy(
        update={"seller": Party(name="Acme sp. z o.o.", nip="1130220180")}
    )
    fired = [v for v in check(broken) if v.rule == "identifiers.nip_checksum"]
    assert len(fired) == 1
    assert fired[0].fields == ("seller.nip",)


def test_absent_nip_is_not_a_violation(invoice):
    """A consumer buyer has no NIP at all; absence is not an error the detector may claim."""
    anonymous = invoice.model_copy(update={"buyer": Party(name="Jan Kowalski")})
    assert "identifiers.nip_checksum" not in rules(anonymous)


def test_bad_iban_is_caught(invoice):
    broken = invoice.model_copy(update={"payment_account": VALID_IBAN[:-1] + "5"})
    assert "identifiers.iban_checksum" in rules(broken)


def test_issue_long_before_sale_is_heuristic_only(invoice):
    early = invoice.model_copy(
        update={"issue_date": dt.date(2026, 1, 1), "sale_date": dt.date(2026, 8, 5)}
    )
    fired = [v for v in check(early) if v.rule == "dates.issue_near_sale"]
    assert len(fired) == 1
    assert fired[0].severity is Severity.HEURISTIC
    # The interpretable half of the signal must exclude it.
    assert hard_violations(early) == ()


def test_issue_within_the_lawful_window_is_quiet(invoice):
    ok = invoice.model_copy(
        update={"issue_date": dt.date(2026, 7, 1), "sale_date": dt.date(2026, 8, 5)}
    )
    assert check(ok) == ()


def test_missing_amounts_do_not_fire_rules(invoice):
    """A simplified row omits amounts; a rule whose inputs are absent must stay silent."""
    bare = LineItem(line_no=9, description="Pozycja bez kwot")
    with_bare = invoice.model_copy(update={"lines": (bare,)})
    assert not any(v.rule.startswith("lines.") for v in check(with_bare))


def test_violations_are_hashable_and_carry_a_stable_id(invoice):
    broken = invoice.model_copy(update={"total_gross": d("400.00")})
    violations = check(broken)
    assert len(set(violations)) == len(violations)
    assert all(isinstance(v.delta, Decimal | type(None)) for v in violations)


def test_a_repeated_rate_code_is_compared_only_once(invoice):
    """Two identical `Violation`s are equal and hash-equal, so they double every per-rule tally.

    `totals.rate_codes_unique` already reports the repetition itself; comparing the same line group
    against it twice adds no information and would inflate the counts the detector study reports.
    """
    wrong = RateTotal(rate="23", net=d("999.00"), vat=d("57.50"))
    doubled = invoice.model_copy(
        update={"rate_totals": (wrong, wrong, invoice.rate_totals[1])}
    )
    violations = check(doubled)
    assert sum(v.rule == "lines.sum_matches_rate_net" for v in violations) == 1
    assert "totals.rate_codes_unique" in rules(doubled)
    assert len(set(violations)) == len(violations)


def test_the_gross_is_checked_against_the_rows_as_well_as_the_rate_totals(invoice):
    """An invented row at a rate with no P_13 block used to leave `check()` completely empty.

    `lines.sum_matches_rate_*` walks the rate totals, so a row carrying a rate the totals never
    mention is never looked at, and `totals.gross_equals_net_plus_vat` reads only the totals. The
    row therefore existed in the extraction, changed nothing any rule compared, and passed.
    """
    invented = LineItem(line_no=99, description="Pozycja zmyślona", quantity=d("1"),
                        unit_price_net=d("999.00"), net=d("999.00"), vat=d("229.77"), vat_rate="23")
    with_extra = invoice.model_copy(update={"lines": (*invoice.lines, invented)})
    assert "totals.gross_equals_line_sum" in rules(with_extra)


def test_a_dropped_row_is_caught_even_when_the_rate_totals_still_agree(invoice):
    """Losing rows is the `multi_page` failure mode, and the gross is what still knows about it."""
    short = invoice.model_copy(update={"lines": invoice.lines[:-1]})
    assert "totals.gross_equals_line_sum" in rules(short)


def test_a_gross_with_nothing_behind_it_is_reported_rather_than_passing(invoice):
    """Empty is not clean: an extraction that returned only the total could check out perfectly."""
    stripped = invoice.model_copy(update={"lines": (), "rate_totals": ()})
    assert "totals.gross_has_no_support" in rules(stripped)
    assert all(v.severity is Severity.HEURISTIC for v in check(stripped))


def test_a_simplified_invoice_is_allowed_to_carry_only_a_total(invoice):
    """`UPR` lawfully has neither rows nor rate totals, so it must not trip the support rule.

    A heuristic that fired on every document of a legitimate kind would be noise, and its false
    positives would be indistinguishable from a real miss — which is what the severity split is
    there to keep apart.
    """
    simplified = invoice.model_copy(
        update={"kind": "UPR", "lines": (), "rate_totals": ()}
    )
    assert "totals.gross_has_no_support" not in rules(simplified)


def test_a_sale_long_after_the_issue_date_is_caught_in_both_directions(invoice):
    """A misread year puts the sale a year *before* the issue, where the old rule stayed silent."""
    misread_year = invoice.model_copy(update={"sale_date": dt.date(2025, 8, 5)})
    assert "dates.issue_follows_sale" in rules(misread_year)
    assert all(v.severity is Severity.HEURISTIC for v in check(misread_year))

    early = invoice.model_copy(update={"sale_date": dt.date(2026, 12, 1)})
    assert "dates.issue_near_sale" in rules(early)


def test_a_negative_row_offset_by_a_positive_one_is_still_a_sign_error(invoice):
    """The totals cannot see it: they still add up, so every summing rule passes."""
    first, second, *rest = invoice.lines
    flipped = (
        first.model_copy(update={"net": -first.net, "vat": -first.vat}),
        second.model_copy(update={"net": second.net + 2 * first.net,
                                  "vat": second.vat + 2 * first.vat}),
        *rest,
    )
    swapped = invoice.model_copy(update={"lines": flipped})
    assert "totals.non_correction_amounts_non_negative" in rules(swapped)


def test_a_correction_may_carry_negative_rows(invoice):
    """The rule exists to catch a misread sign, not to forbid the document type that needs one."""
    negatives = tuple(
        line.model_copy(update={"net": -line.net, "vat": -line.vat}) for line in invoice.lines
    )
    correction = invoice.model_copy(update={
        "kind": "KOR",
        "lines": negatives,
        "rate_totals": tuple(
            total.model_copy(update={"net": -total.net, "vat": -total.vat})
            for total in invoice.rate_totals
        ),
        "total_gross": -invoice.total_gross,
    })
    assert "totals.non_correction_amounts_non_negative" not in rules(correction)
