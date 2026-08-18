"""The gold must be arithmetically coherent, and each tier must actually carry its own difficulty.

The first is the load-bearing one. The detector study in M5 asks whether an invariant violation
predicts an extraction error; if the *gold* could break an invariant, the study would be measuring
the generator. So every document of every tier is required to come back from `invariants.check()`
with nothing at all — including the heuristic rules, whose false positives on correct documents
would be indistinguishable from a real miss.

The second stops the difficulty taxonomy from being decoration. A `mixed_rates` document that drew
four rows at 23 % is a `clean` document with a different label, and a per-tier accuracy table built
on that says nothing.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from doc_extract.schema import invariants, vocab
from doc_extract.schema.checksums import is_valid_iban, is_valid_nip
from doc_extract.synth.build import build
from doc_extract.synth.corpus import documents
from doc_extract.synth.tiers import TIERS, Tier

#: Seeds for the tests that explore *beyond* the corpus, to widen the draws each tier is asked to
#: survive. The corpus itself is not built this way — see the `corpus` fixture.
PER_TIER = 6


@pytest.fixture(scope="module")
def corpus():
    """The corpus as it ships — `documents()` at its own defaults, no arguments.

    Building it costs about 30 ms, so there is nothing to buy by testing a smaller or differently
    seeded stand-in. There is something to lose: a document id maps to its own seed, so a fixture
    that made up its own seeds would test invoices the corpus never contains, and leave the ones it
    does contain unchecked. That gap is how an M4 run could be computed on documents no test ever
    looked at.
    """
    return list(documents())


@pytest.mark.parametrize("tier", TIERS, ids=lambda tier: tier.name)
def test_the_shipped_corpus_satisfies_every_invariant(corpus, tier: Tier):
    """No document an M4/M5 run is computed on may break a rule the extractor is judged by."""
    for document in [entry for entry in corpus if entry.tier == tier.name]:
        violations = invariants.check(document.invoice)
        assert violations == (), (
            f"{document.doc_id} breaks its own gold: "
            + "; ".join(f"{v.rule} ({v.message})" for v in violations)
        )


@pytest.mark.parametrize("tier", TIERS, ids=lambda tier: tier.name)
def test_gold_satisfies_every_invariant_on_seeds_beyond_the_corpus(tier: Tier):
    """The same requirement on draws the corpus does not contain, so a re-seed holds no surprises.

    `money.apportion` raises when a split cannot be reconciled, so the tier that would break it
    should fail here rather than the first time somebody regenerates with a different seed.
    """
    for index in range(PER_TIER):
        document = build(tier, seed=1_000 + index,
                         doc_id=f"{tier.name}-{index}", template="classic")
        violations = invariants.check(document.invoice)
        assert violations == (), (
            f"{tier.name} #{index} breaks its own gold: "
            + "; ".join(f"{v.rule} ({v.message})" for v in violations)
        )


def test_the_same_seed_gives_the_same_invoice():
    """Reproducibility is the corpus's substitute for being committed."""
    first = build(TIERS[0], seed=42, doc_id="x", template="classic")
    second = build(TIERS[0], seed=42, doc_id="x", template="classic")
    assert first.invoice == second.invoice
    assert first.context == second.context


def test_different_seeds_give_different_invoices():
    assert build(TIERS[0], seed=1, doc_id="x", template="classic").invoice != \
        build(TIERS[0], seed=2, doc_id="x", template="classic").invoice


@pytest.mark.parametrize("tier", TIERS, ids=lambda tier: tier.name)
def test_every_rate_the_tier_names_actually_appears(tier: Tier):
    """Otherwise a mixed-rate tier can quietly degenerate into a single-rate one."""
    for index in range(PER_TIER):
        document = build(tier, seed=2_000 + index,
                         doc_id=f"{tier.name}-{index}", template="classic")
        assert {total.rate for total in document.invoice.rate_totals} == set(tier.rates)


def test_correction_invoices_carry_negative_amounts():
    """A korekta that reduced nothing would exercise none of the sign handling it exists for."""
    for index in range(PER_TIER):
        document = build(_tier("correction"), seed=3_000 + index, doc_id="k", template="classic")
        assert document.invoice.is_correction
        assert document.invoice.total_gross < 0
        assert all(line.net < 0 for line in document.invoice.lines)


def test_non_corrections_never_carry_negative_amounts():
    for tier in TIERS:
        if tier.kind in vocab.CORRECTION_KINDS:
            continue
        document = build(tier, seed=4_000, doc_id="p", template="classic")
        assert document.invoice.total_gross > 0


def test_the_rounding_tier_really_needs_rounding():
    """Eight-decimal prices are the point of the tier; two-decimal ones would make it `clean`."""
    document = build(_tier("grosz_rounding"), seed=5_000, doc_id="g", template="classic")
    inexact = [
        line for line in document.invoice.lines
        if line.net != line.quantity * line.unit_price_net - (line.discount or Decimal(0))
    ]
    assert inexact, "no line total needed rounding, so the tier tests nothing"


def test_the_multi_page_tier_has_enough_rows_to_spill():
    document = build(_tier("multi_page"), seed=6_000, doc_id="m", template="classic")
    assert len(document.invoice.lines) >= 26


def test_reverse_charge_levies_no_tax():
    document = build(_tier("reverse_charge"), seed=7_000, doc_id="r", template="classic")
    assert all(total.vat == 0 for total in document.invoice.rate_totals)
    assert document.context.annotations.reverse_charge


def test_the_foreign_currency_tier_restates_the_tax_in_zloty():
    """`P_14_xW` is a second set of amounts on the page that are not the invoice's own."""
    document = build(_tier("foreign_currency"), seed=8_000, doc_id="f", template="classic")
    assert document.invoice.currency == "EUR"
    assert document.context.fx_rate is not None
    assert len(document.context.vat_in_pln) == len(document.invoice.rate_totals)


def test_split_payment_always_carries_the_account_it_must_be_paid_to(corpus):
    """The mechanism is meaningless without one, and the annotation would be a lie."""
    for document in corpus:
        if document.tier == "split_payment":
            assert document.invoice.payment_account is not None
            assert document.context.annotations.split_payment


def test_identifiers_pass_the_check_digits_the_invariants_will_apply(corpus):
    for document in corpus:
        assert is_valid_nip(document.invoice.seller.nip)
        assert is_valid_nip(document.invoice.buyer.nip)
        if document.invoice.payment_account is not None:
            assert is_valid_iban(document.invoice.payment_account, country="PL")


def test_amounts_stay_in_a_plausible_business_range(corpus):
    """A six-figure line total teaches an extractor nothing about reading a real invoice."""
    for document in corpus:
        assert all(abs(line.net) < Decimal(60_000) for line in document.invoice.lines)


def test_units_are_recorded_for_every_line(corpus):
    """The unit is on the page but outside the extraction schema; the two must stay aligned."""
    for document in corpus:
        assert len(document.context.line_units) == len(document.invoice.lines)


def _tier(name: str) -> Tier:
    from doc_extract.synth.tiers import BY_NAME

    return BY_NAME[name]
