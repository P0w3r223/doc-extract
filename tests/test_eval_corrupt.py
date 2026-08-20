"""The injected errors have to be reproducible, lawful, and — crucially — not all detectable.

B3 exists to give M5 a labelled error set. That only works if two things hold, and they pull in
opposite directions: every corruption must still produce an invoice the schema admits (otherwise it
is a malformed document, not a misreading), and the set as a whole must contain errors the
invariants *cannot* see (otherwise the detector's recall is 1.0 by construction).
"""

from __future__ import annotations

import datetime as dt
import random
from decimal import Decimal

import pytest

from doc_extract.eval import corrupt
from doc_extract.schema import invariants
from doc_extract.schema.checksums import is_valid_iban, is_valid_nip
from doc_extract.schema.invariants import Severity
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.tiers import BY_NAME as TIERS


def _plain(value: Decimal) -> str:
    """The form a note writes an amount in, so a comparison is against the note and not a repr."""
    return format(value, "f")

ALWAYS = 1.0


def _one(kind: str, invoice, seed: int = 0):
    """Apply exactly one named corruption, so a test is about that corruption and nothing else."""
    corruption = dict(corrupt.CORRUPTIONS)[kind]
    return corruption(invoice, random.Random(seed))


def test_the_same_seed_injects_the_same_errors(invoice):
    first = corrupt.corrupt(invoice, random.Random(7), rate=0.5)
    second = corrupt.corrupt(invoice, random.Random(7), rate=0.5)
    assert first == second


def test_a_rate_of_zero_is_the_oracle(invoice):
    corrupted, injections = corrupt.corrupt(invoice, random.Random(1), rate=0.0)
    assert corrupted == invoice
    assert injections == ()


def test_a_rate_of_one_fires_every_kind_that_can_still_be_recorded_truthfully(invoice):
    """Ten kinds, eight records: two of them would write over a field already recorded.

    `year_misread` and `date_shifted` both write `sale_date`, and on this one-rate-block fixture
    `rate_swapped` rewrites the very block `vat_cent` was recorded against. The loser of each pair
    is dropped rather than allowed to falsify the other's note. So the contract is not "ten fired"
    but "one injection per field", and this says what that costs and which way the order resolves
    it — a document with two rate blocks keeps both, which the regression below uses.
    """
    _, injections = corrupt.corrupt(invoice, random.Random(1), rate=ALWAYS)
    fired = {injection.kind for injection in injections}

    assert fired == set(corrupt.KINDS) - {"date_shifted", "rate_swapped"}
    assert "year_misread" in fired, "the heuristic half's only kind must not lose the collision"


def test_no_injection_writes_over_a_field_another_one_recorded(invoice):
    """The guard's actual contract, and it is containment rather than equality.

    A field path and its parent are two strings and one value: `rate_swapped` names
    `rate_totals[zw]` while `vat_cent` names `rate_totals[zw].vat`, and the swap rewrites the block
    the cent was recorded against. Comparing the strings for equality let exactly that through, so
    this asserts the relation the record depends on instead of the one that is easy to check.
    """
    _, injections = corrupt.corrupt(invoice, random.Random(1), rate=ALWAYS)
    fields = [injection.field for injection in injections]

    overlapping = [
        (one, other)
        for index, one in enumerate(fields)
        for other in fields[index + 1:]
        if one == other or one.startswith(f"{other}.") or other.startswith(f"{one}.")
    ]
    assert not overlapping, overlapping


def test_a_nested_field_does_not_survive_a_corruption_of_the_block_it_sits_in():
    """The regression, on a document that actually has two rate blocks to collide over.

    Driven off an invoice from the corpus rather than the fixture, because the collision needs a
    rate block whose net and VAT differ *and* a second one for `vat_cent` to pick — which is the
    shape `mixed_rates` has and the single-block fixture does not.
    """
    document = next(
        doc for doc in synth_corpus.documents(per_tier=1, tiers=(TIERS["mixed_rates"],))
    )
    corrupted, injections = corrupt.corrupt(document.invoice, random.Random(1), rate=ALWAYS)

    blocks = {total.rate: total for total in corrupted.rate_totals}
    for injection in injections:
        if not injection.field.endswith("].vat"):
            continue
        rate = injection.field.split("[", 1)[1].split("]", 1)[0]
        assert _plain(blocks[rate].vat) == injection.after, injection.note


def test_every_corruption_still_produces_a_lawful_invoice(invoice):
    """A schema violation would be a malformed document; these are misreadings of a valid one."""
    for kind in corrupt.KINDS:
        applied = _one(kind, invoice)
        assert applied is not None, kind
        corrupted, _ = applied
        assert corrupted != invoice, kind


@pytest.mark.parametrize(
    "kind", ["total_transposed", "vat_cent", "rate_swapped", "line_dropped", "line_transposed"]
)
def test_the_arithmetic_corruptions_break_a_hard_rule(kind, invoice):
    """The fixture satisfies every invariant, so any hard violation here is the injected one."""
    assert invariants.check(invoice) == ()
    corrupted, injection = _one(kind, invoice)
    hard = invariants.hard_violations(corrupted)
    assert hard, f"{injection.note} went unnoticed by every hard rule"


def test_the_identifier_corruptions_break_a_check_digit(invoice):
    corrupted, _ = _one("nip_digit", invoice)
    assert not is_valid_nip(corrupted.seller.nip or "")

    corrupted, _ = _one("account_digit", invoice)
    assert not is_valid_iban(corrupted.payment_account or "")


@pytest.mark.parametrize("kind", sorted(corrupt.INVISIBLE_KINDS))
def test_the_invisible_corruptions_are_invisible(kind, invoice):
    """These are the reason the detector study is worth running: wrong, and arithmetically silent.

    A hard rule that started catching one of them would be a change of claim, not a bug fix — the
    date rule is deliberately `HEURISTIC`, because an invoice may lawfully precede its sale.
    """
    corrupted, _ = _one(kind, invoice)
    assert corrupted != invoice
    assert not [
        violation for violation in invariants.check(corrupted)
        if violation.severity is Severity.HARD
    ]


def test_every_kind_declares_which_severity_should_catch_it():
    """A kind absent from `CAUGHT_BY` would print in the per-kind table with no label at all.

    The mapping is what lets a zero mean "not asked" rather than "missed", so a kind added without
    one would quietly read as a detector failure at whichever severity happened to report it.
    """
    assert set(corrupt.CAUGHT_BY) == set(corrupt.KINDS)


@pytest.mark.parametrize("kind", corrupt.KINDS)
def test_caught_by_is_asserted_against_the_rules_and_not_trusted(kind, invoice):
    """What `CAUGHT_BY` claims is what `invariants` actually does to that corruption.

    This is the check the whole per-kind table rests on. Declaring a kind heuristic-only and having
    a hard rule catch it would inflate hard recall; declaring it hard and having a heuristic catch
    it would inflate the half of the rule set that has lawful exceptions. Either way the severity
    split — the thing that keeps a heuristic's false positives out of the arithmetic's precision —
    would be reported wrongly, and nothing else in the suite would notice.
    """
    assert invariants.check(invoice) == (), "the fixture must start clean for this to mean anything"
    corrupted, injection = _one(kind, invoice)
    fired = {violation.severity for violation in invariants.check(corrupted)}
    expected = corrupt.CAUGHT_BY[kind]

    if expected is None:
        assert not fired, f"{injection.note} was declared invisible and {fired} saw it"
    else:
        assert fired == {expected}, f"{injection.note} was declared {expected} and fired {fired}"


def test_a_misread_year_is_caught_by_the_date_rule_and_by_nothing_else(invoice):
    """The corruption exists to exercise a rule that had never fired; name the rule it fires.

    Asserting the severity alone would pass if some unrelated heuristic caught it for an unrelated
    reason, and the point of the kind is that `dates.issue_near_sale` — widened for exactly this
    reading error — is what sees it.
    """
    corrupted, injection = _one("year_misread", invoice)
    rules = {violation.rule for violation in invariants.check(corrupted)}

    assert rules <= {"dates.issue_near_sale", "dates.issue_follows_sale"}
    assert rules, f"{injection.note} fired nothing"
    assert corrupted.sale_date.year != invoice.sale_date.year
    assert (corrupted.sale_date.month, corrupted.sale_date.day) == (
        invoice.sale_date.month, invoice.sale_date.day
    )


def test_a_leap_day_survives_the_year_it_cannot_be_moved_to(invoice):
    """29 February is moved to the 28th rather than raising, so no document is silently skipped."""
    leap = invoice.model_copy(update={"sale_date": dt.date(2024, 2, 29)})
    corrupted, _ = _one("year_misread", leap)
    assert corrupted.sale_date in (dt.date(2023, 2, 28), dt.date(2025, 2, 28))


def test_a_transposition_keeps_the_sign_and_the_decimal_places(invoice):
    negative = invoice.model_copy(update={"total_gross": Decimal("-2214.15")})
    corrupted, injection = _one("total_transposed", negative)

    assert corrupted.total_gross < 0
    assert -corrupted.total_gross.as_tuple().exponent == 2
    assert injection.kind == "total_transposed"
    assert injection.before == "-2214.15"


def test_a_note_names_the_kind_first(invoice):
    """M5 groups by kind, and it does so by reading the first token of the note."""
    _, injection = _one("vat_cent", invoice)
    assert injection.note.split(" ", 1)[0] == "vat_cent"
    assert " -> " in injection.note


def test_a_document_with_nothing_to_break_is_left_alone():
    """A corruption that cannot apply returns nothing rather than inventing something to change."""
    from doc_extract.eval.baselines import CONSTANT_INVOICE

    assert _one("line_dropped", CONSTANT_INVOICE) is None
    assert _one("vat_cent", CONSTANT_INVOICE) is None
    assert _one("nip_digit", CONSTANT_INVOICE) is None
