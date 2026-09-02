"""The detector study has to be a measurement, not a construction.

Three things could quietly turn it into one, and each has a test here. A verdict set that did not
partition would let a document be counted twice. A document with no prediction counted as a catch
would credit the invariants with the pipeline's own refusal. And a per-kind recall that attributed a
firing to whichever injected kind happened to be listed first would report the visible kinds' recall
against the invisible ones' names.

The claim the study exists to make — that some errors are arithmetically invisible — is asserted
against the rule set in `test_eval_corrupt.py` rather than trusted. What is asserted here is that
the *counting* of it is honest.
"""

from __future__ import annotations

import datetime as dt
import random
from decimal import Decimal

import pytest

from conftest import totals_only
from doc_extract.eval import corrupt, detector, fields
from doc_extract.eval.detector import Counts, Verdict
from doc_extract.eval.scorer import judge
from doc_extract.extract.result import FailureClass
from doc_extract.schema import invariants
from doc_extract.schema.invariants import Severity


def _score(gold, prediction, *, doc_id="doc-0000", failure=FailureClass.NONE):
    return judge(
        gold, prediction, doc_id=doc_id,
        facets=(("tier", "clean"), ("template", "classic")), failure=failure
    )


def _verdict(gold, prediction, *, severity=Severity.HARD, notes=()):
    return detector.verdict(
        _score(gold, prediction), prediction, severity=severity, notes=notes
    )


def _break(kind: str, invoice, seed: int = 0):
    corrupted, injection = dict(corrupt.CORRUPTIONS)[kind](invoice, random.Random(seed))
    return corrupted, (injection.note,)


# --------------------------------------------------------------------------- the four verdicts


def test_a_perfect_reading_is_a_true_negative(invoice):
    """The control the whole study rests on: correct gold must not trip a single hard rule."""
    assert invariants.hard_violations(invoice) == ()
    assert _verdict(invoice, invoice).verdict is Verdict.TRUE_NEGATIVE


def test_an_arithmetic_error_is_a_true_positive(invoice):
    corrupted, notes = _break("vat_cent", invoice)
    row = _verdict(invoice, corrupted, notes=notes)

    assert row.verdict is Verdict.TRUE_POSITIVE
    assert row.rules
    assert row.wrong_fields


def test_an_invisible_error_is_a_false_negative(invoice):
    """The finding, as a verdict: the fields are wrong and every hard rule stays silent."""
    corrupted, notes = _break("name_truncated", invoice)
    row = _verdict(invoice, corrupted, notes=notes)

    assert row.verdict is Verdict.FALSE_NEGATIVE
    assert row.rules == ()
    assert "buyer.name" in row.wrong_fields


def test_a_rule_that_fires_on_a_correct_reading_is_a_false_positive(invoice):
    """Constructed rather than found — the hard rules produce none on this corpus.

    A heuristic can fire on a document that was read perfectly, because its exceptions are lawful.
    Scoring that as a true positive is the mistake this verdict exists to prevent, so the case is
    built by hand instead of waiting for a corpus that happens to contain one.
    """
    lawful = totals_only(
        net="100.00", vat="23.00", gross="123.00",
        sale_date=dt.date(2027, 6, 1),  # far enough ahead to trip the heuristic date rule
    )
    row = _verdict(lawful, lawful, severity=Severity.HEURISTIC)

    assert row.rules == ("dates.issue_near_sale",)
    assert row.wrong_fields == ()
    assert row.verdict is Verdict.FALSE_POSITIVE


def test_no_prediction_is_its_own_verdict_and_not_a_miss(invoice):
    """An extraction that produced nothing gave the rules nothing to read."""
    score = _score(invoice, None, failure=FailureClass.SCHEMA_INVALID)
    row = detector.verdict(score, None)

    assert row.verdict is Verdict.NO_PREDICTION
    assert row.rules == ()
    assert row.wrong_fields, "every gold field is missed, so the document is still wrong"


# --------------------------------------------------------------------------- the counting


def test_the_verdicts_partition_the_documents(invoice):
    corrupted, _ = _break("vat_cent", invoice)
    truncated, _ = _break("name_truncated", invoice)
    rows = [
        _verdict(invoice, invoice),
        _verdict(invoice, corrupted),
        _verdict(invoice, truncated),
        detector.verdict(_score(invoice, None, failure=FailureClass.SCHEMA_INVALID), None),
    ]
    study = detector.summarise(rows)
    counts = study.counts

    assert counts.documents == len(rows)
    assert counts.judged == 3
    assert counts.no_prediction == 1
    assert counts.true_negative + counts.true_positive + counts.false_negative == counts.judged


def test_a_document_with_no_prediction_is_outside_every_denominator(invoice):
    """It must move `documents` and nothing else — not recall, not precision, not prevalence."""
    corrupted, _ = _break("vat_cent", invoice)
    without = detector.summarise([_verdict(invoice, invoice), _verdict(invoice, corrupted)])
    with_gap = detector.summarise([
        _verdict(invoice, invoice),
        _verdict(invoice, corrupted),
        detector.verdict(_score(invoice, None, failure=FailureClass.SCHEMA_INVALID), None),
    ])

    assert with_gap.counts.documents == without.counts.documents + 1
    assert with_gap.counts.judged == without.counts.judged
    assert with_gap.counts.recall == without.counts.recall
    assert with_gap.counts.precision == without.counts.precision
    assert with_gap.counts.prevalence == without.counts.prevalence


def test_a_rate_with_no_denominator_is_none_and_never_zero():
    """The rule the whole `eval` package follows: an absent measurement is not a measured 0."""
    empty = Counts()
    assert empty.precision is None
    assert empty.recall is None
    assert empty.specificity is None
    assert empty.prevalence is None
    assert empty.f1 is None


def test_f1_is_zero_when_the_detector_caught_nothing_it_could_have():
    """Nothing found, but there was something to find and something was flagged: a real zero.

    This is the one place `0.0` is right where the rest of the package returns `None`. Both
    denominators exist, so the question was asked and the answer is that the detector failed.
    """
    missed = Counts(true_positive=0, false_positive=3, false_negative=5, true_negative=1)
    assert missed.precision == 0.0
    assert missed.recall == 0.0
    assert missed.f1 == 0.0


def test_prevalence_is_reported_so_recall_can_be_read(invoice):
    """A detector that flags everything scores a perfect recall; prevalence is what shows it."""
    corrupted, _ = _break("vat_cent", invoice)
    study = detector.summarise([_verdict(invoice, corrupted), _verdict(invoice, invoice)])

    assert study.counts.recall == 1.0
    assert study.counts.prevalence == 0.5


# --------------------------------------------------------------------------- per kind


def test_a_kind_is_read_off_the_front_of_its_note(invoice):
    _, notes = _break("vat_cent", invoice)
    assert detector.kinds(notes) == ("vat_cent",)


def test_a_note_this_package_did_not_write_is_not_a_labelled_error():
    """An unrecognised leading token is dropped rather than becoming a row in the kind table."""
    assert detector.kinds(("smudged total_gross: 1 -> 2",)) == ()
    assert detector.kinds(("vat_cent x: 1 -> 2", "invented y: 3 -> 4")) == ("vat_cent",)


def test_isolated_recall_ignores_documents_carrying_more_than_one_kind(invoice):
    """The contamination the two readings exist to separate.

    A document carrying both an invisible error and a visible one fires, and counting that towards
    the invisible kind would report the visible kind's recall under the invisible one's name.
    """
    both, _ = _break("name_truncated", invoice)
    both, _ = _break("vat_cent", both)
    alone, _ = _break("name_truncated", invoice)

    study = detector.summarise([
        _verdict(invoice, both, notes=("name_truncated buyer.name: a b -> a",
                                       "vat_cent rate_totals[23].vat: 1 -> 2")),
        _verdict(invoice, alone, notes=("name_truncated buyer.name: a b -> a",)),
    ])
    by_kind = {row.kind: row for row in study.kinds}

    assert by_kind["name_truncated"].marginal_documents == 2
    assert by_kind["name_truncated"].marginal_recall == 0.5    # contaminated
    assert by_kind["name_truncated"].isolated_documents == 1
    assert by_kind["name_truncated"].isolated_recall == 0.0    # the honest number
    assert by_kind["name_truncated"].expected_invisible


def test_kinds_never_injected_are_left_out_entirely(invoice):
    """A run that injects nothing gets no kind table, rather than nine rows of dashes."""
    assert detector.summarise([_verdict(invoice, invoice)]).kinds == ()


# --------------------------------------------------------------------------- localisation


def test_localisation_is_only_asked_of_a_true_positive(invoice):
    corrupted, _ = _break("vat_cent", invoice)
    truncated, _ = _break("name_truncated", invoice)

    assert _verdict(invoice, corrupted).localised is True
    assert _verdict(invoice, invoice).localised is None
    assert _verdict(invoice, truncated).localised is None


def test_a_rule_that_points_at_the_wrong_place_is_not_localised(invoice):
    """Caught, but for the wrong reason — a true positive that explains nothing.

    The page itself carries a NIP that fails its check digit, and the extractor transcribes it
    faithfully, as `prompt` requires it to. The rule fires on a field that was read *correctly*
    while the one genuine misreading is a name no arithmetic touches. The document is flagged, and
    the reason given is about the wrong field — which is why localisation is reported apart from
    recall rather than folded into it.
    """
    gold = invoice.model_copy(update={
        "seller": invoice.seller.model_copy(update={"nip": "1130220188"}),  # bad digit on the page
    })
    prediction = gold.model_copy(update={
        "buyer": gold.buyer.model_copy(update={"name": "Klient"}),
    })
    row = _verdict(gold, prediction)

    assert row.verdict is Verdict.TRUE_POSITIVE
    assert row.rules == ("identifiers.nip_checksum",)
    assert row.wrong_fields == ("buyer.name",)
    assert row.named_fields == ("seller.nip",)
    assert row.localised is False


# --------------------------------------------------------------------------- the field mapping


def test_every_field_a_rule_names_maps_onto_something_scored(invoice):
    """Drift guard. A new rule naming a field the scorer does not know would stop contributing to
    localisation while still counting towards recall, and nothing else would notice.

    The sweep is every corruption applied to the fixture, plus the shape rules that need a document
    the corruptions cannot produce — which between them fire every rule in `invariants`.
    """
    documents = [corrupt.corrupt(invoice, random.Random(seed), rate=1.0)[0] for seed in range(8)]
    documents.append(totals_only(net="100.00", vat="8.00", gross="108.00"))
    documents.append(totals_only(net="0", vat="0", gross="500.00", kind="ZAL"))
    documents.append(invoice.model_copy(update={"total_gross": Decimal("-1.00")}))

    named = {
        part
        for document in documents
        for violation in invariants.check(document)
        for part in violation.fields
    }
    assert named, "the sweep fired no rule at all, so it is asserting nothing"

    unmapped = sorted(part for part in named if not detector.covered(part))
    assert unmapped == [], f"rules name fields the scorer does not score: {unmapped}"


def test_covered_expands_a_collection_to_its_scored_members():
    assert detector.covered("total_gross") == ("total_gross",)
    assert detector.covered("rate_totals") == ("rate_totals[].net", "rate_totals[].vat")
    assert set(detector.covered("lines")) == {
        field.name for field in fields.FIELDS if field.name.startswith("lines[].")
    }


def test_covered_returns_empty_rather_than_guessing():
    assert detector.covered("nonesuch") == ()


# --------------------------------------------------------------------------- severity


@pytest.mark.parametrize("severity", list(Severity))
def test_the_two_severities_are_counted_apart(severity, invoice):
    """Pooling them would let heuristics borrow the precision of rules that have no exceptions."""
    corrupted, _ = _break("vat_cent", invoice)
    row = _verdict(invoice, corrupted, severity=severity)

    fired = {v.rule for v in invariants.check(corrupted) if v.severity is severity}
    assert set(row.rules) == fired


# --------------------------------------------------------------------------- rendering


def _meta(model="claude-opus-5", baseline="claude"):
    from doc_extract.eval.predictions import RunMeta

    return RunMeta(
        baseline=baseline, model=model, corpus_dir="data/synthetic", documents=1,
        max_tokens=16000, repair_max_tokens=8192, max_repairs=1, options={"sees": "the page"},
    )


def test_a_study_with_nothing_to_detect_prints_dashes_and_says_why(invoice):
    """`claude` on this corpus is exactly this case, so the wording is load-bearing."""
    from doc_extract.eval import detector_report

    study = detector.summarise([_verdict(invoice, invoice)])
    rendered = detector_report.render(study, run=_meta())

    assert "| recall | — |" in rendered
    assert "0.0 %" not in rendered.split("## Read this")[0].split("| recall |")[1][:20]
    assert "nothing to detect" in rendered
    assert "false-positive rate" in rendered


def test_a_rendered_study_never_turns_an_absent_rate_into_a_zero(invoice):
    from doc_extract.eval import detector_report

    truncated, notes = _break("name_truncated", invoice)
    study = detector.summarise([_verdict(invoice, truncated, notes=notes)])
    rendered = detector_report.render(study, run=_meta())

    assert "| precision | — |" in rendered, "nothing was flagged, so precision has no denominator"
    assert "| recall | 0.0 % |" in rendered, "something was wrong and missed: a measured zero"
    assert "declared invisible" in rendered
