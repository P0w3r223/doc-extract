"""The injected errors have to be reproducible, lawful, and — crucially — not all detectable.

B3 exists to give M5 a labelled error set. That only works if two things hold, and they pull in
opposite directions: every corruption must still produce an invoice the schema admits (otherwise it
is a malformed document, not a misreading), and the set as a whole must contain errors the
invariants *cannot* see (otherwise the detector's recall is 1.0 by construction).
"""

from __future__ import annotations

import random
from decimal import Decimal

import pytest

from doc_extract.eval import corrupt
from doc_extract.schema import invariants
from doc_extract.schema.checksums import is_valid_iban, is_valid_nip
from doc_extract.schema.invariants import Severity

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


def test_a_rate_of_one_fires_everything_it_can(invoice):
    _, injections = corrupt.corrupt(invoice, random.Random(1), rate=ALWAYS)
    assert {injection.kind for injection in injections} == set(corrupt.KINDS)


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
