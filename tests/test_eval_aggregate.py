"""Counts, the rates that follow from them, and the coverage check that gates both.

The rule these tests exist for is the one that is easiest to break by accident: a metric with no
denominator has to be `None`, not zero. Every other guarantee here — support on every row, coverage
asserted before anything is reported, cost summed over failed attempts too — is a rule from
`CLAUDE.md` with a test in front of it.
"""

from __future__ import annotations

import pytest

from doc_extract.eval import report as eval_report
from doc_extract.eval.aggregate import Coverage, CoverageError, Scored, Tally, summarise, tally
from doc_extract.eval.predictions import AttemptRecord, Prediction, RunMeta
from doc_extract.eval.scorer import Outcome, Result, judge
from doc_extract.extract.result import FailureClass, Stage

RUN = RunMeta(
    baseline="oracle", model="oracle", corpus_dir="data/synthetic", documents=2,
    max_tokens=8192, repair_max_tokens=4096, max_repairs=1,
)


def _prediction(doc_id: str, *, failure: str = "none", attempts: tuple = ()) -> Prediction:
    return Prediction(
        doc_id=doc_id, tier="clean", template="classic", pdf_sha256="0" * 64,
        failure=failure, stop_reason="end_turn", attempts=attempts, invoice={},
    )


def _attempt(stage: Stage, output: int, failure: str = "none") -> AttemptRecord:
    return AttemptRecord(
        stage=str(stage), model="m", stop_reason="end_turn", failure=failure,
        input_tokens=100, output_tokens=output,
        cache_creation_input_tokens=0, cache_read_input_tokens=0,
    )


def _scored(invoice, prediction_invoice, doc_id="clean-0000", **over) -> Scored:
    return Scored(
        prediction=_prediction(doc_id, **over),
        score=judge(invoice, prediction_invoice, doc_id=doc_id,
                    facets=(("tier", "clean"), ("template", "classic")),
                    failure=FailureClass.NONE),
    )


def test_a_rate_with_no_denominator_is_none_and_not_zero():
    """The failure mode is silent: `0.0` reads as a measurement, and nothing was measured."""
    empty = Tally()
    assert empty.support == 0
    assert empty.accuracy is None
    assert empty.detection_recall is None
    assert empty.detection_precision is None
    assert empty.value_accuracy is None


def test_the_three_rates_answer_three_different_questions():
    counts = tally([
        Result("f", "", Outcome.CORRECT, "a", "a"),
        Result("f", "", Outcome.WRONG, "b", "c"),
        Result("f", "", Outcome.MISSED, "d", None),
        Result("f", "", Outcome.SPURIOUS, None, "e"),
        Result("f", "", Outcome.ABSENT, None, None),
    ])
    assert counts.support == 3                       # correct + wrong + missed
    assert counts.detection_recall == pytest.approx(2 / 3)
    assert counts.detection_precision == pytest.approx(2 / 3)
    assert counts.value_accuracy == pytest.approx(1 / 2)
    assert counts.accuracy == pytest.approx(1 / 3)
    assert counts.instances == 5


def test_a_perfect_run_scores_one_on_every_field(invoice):
    report = summarise([_scored(invoice, invoice)], run=RUN, expected=["clean-0000"])
    assert report.overall.accuracy == 1.0
    assert report.exact == 1
    assert report.extracted == 1
    assert all(counts.wrong == 0 for _, counts in report.by_field)


def test_support_is_reported_per_field(invoice):
    report = summarise([_scored(invoice, invoice)], run=RUN, expected=["clean-0000"])
    by_field = dict(report.by_field)
    assert by_field["lines[].net"].support == len(invoice.lines)
    assert by_field["total_gross"].support == 1
    #: The fixture carries no discount on any row, so the field has support and no accuracy.
    assert by_field["lines[].discount"].support == 0
    assert by_field["lines[].discount"].accuracy is None
    assert "lines[].discount" in report.unsupported_fields


def test_scoring_a_subset_is_refused_unless_it_is_asked_for(invoice):
    scored = [_scored(invoice, invoice)]
    with pytest.raises(CoverageError, match="scored 1 of the 2"):
        summarise(scored, run=RUN, expected=["clean-0000", "clean-0001"])

    partial = summarise(scored, run=RUN, expected=["clean-0000", "clean-0001"], allow_partial=True)
    assert partial.coverage.complete is False
    assert partial.coverage.missing == ("clean-0001",)


def test_a_prediction_for_a_document_the_corpus_lacks_is_a_coverage_failure(invoice):
    scored = [_scored(invoice, invoice, doc_id="ghost-0000")]
    coverage = Coverage(expected=("clean-0000",), scored=("ghost-0000",))
    assert coverage.unexpected == ("ghost-0000",)
    with pytest.raises(CoverageError, match="not in the manifest"):
        summarise(scored, run=RUN, expected=["clean-0000"])


def test_cost_is_summed_over_every_attempt_including_the_failed_one(invoice):
    """Reporting the winning call alone would make a repairing pipeline look as cheap as one that
    never repairs — which is the whole reason the rule exists."""
    attempts = (
        _attempt(Stage.EXTRACT, output=700, failure="schema_invalid"),
        _attempt(Stage.REPAIR, output=300),
    )
    report = summarise(
        [_scored(invoice, invoice, attempts=attempts)], run=RUN, expected=["clean-0000"]
    )
    assert report.usage.output_tokens == 1000
    assert report.usage.input_tokens == 200
    assert report.attempts == 2
    assert report.repairs == 1


def test_failure_classes_are_counted_as_a_partition(invoice):
    scored = [
        _scored(invoice, invoice, doc_id="a"),
        _scored(invoice, None, doc_id="b", failure="truncated"),
        _scored(invoice, None, doc_id="c", failure="truncated"),
    ]
    report = summarise(scored, run=RUN, expected=["a", "b", "c"])
    assert dict(report.failures) == {"truncated": 2, "none": 1}
    assert sum(count for _, count in report.failures) == report.documents


def test_a_corpus_is_reported_by_the_axes_it_declares_and_not_by_two_fixed_names(invoice):
    """The held-out case, end to end: axes this project's generator never produces get their own
    tables, with the heading and key taken from the corpus rather than from `report.py`.

    Both halves are asserted, because either alone is satisfiable without the other: the tallies
    have to be grouped by the new axes, *and* the rendered document has to carry a table per axis
    and no table for `tier`. The byte-identity of the 24 committed reports is the other side of
    this contract and lives in `tests/test_results_committed.py`.
    """
    scored = [
        Scored(
            prediction=_prediction(doc_id),
            score=judge(invoice, invoice, doc_id=doc_id,
                        facets=(("issuer", issuer), ("legibility", legibility)),
                        failure=FailureClass.NONE),
        )
        for doc_id, issuer, legibility in [
            ("a", "comarch", "born-digital"), ("b", "ifirma", "scan"), ("c", "comarch", "scan"),
        ]
    ]
    report = summarise(scored, run=RUN, expected=["a", "b", "c"])

    assert [name for name, _ in report.by_facet] == ["issuer", "legibility"]
    assert [name for name, _ in report.facet("issuer")] == ["comarch", "ifirma"]
    assert report.by_tier == (), "a corpus with no tier must not grow one"

    body = eval_report.render(report)
    assert "## Per issuer" in body and "| issuer |" in body
    assert "## Per legibility" in body
    assert "## Per tier" not in body


def test_tiers_are_reported_in_the_order_the_corpus_declares_them(invoice):
    """Alphabetical would put `advance` ahead of the `clean` arm every tier is read against."""
    scored = [
        Scored(
            prediction=_prediction(doc_id),
            score=judge(invoice, invoice, doc_id=doc_id,
                        facets=(("tier", tier), ("template", "classic")),
                        failure=FailureClass.NONE),
        )
        for doc_id, tier in [("a", "clean"), ("b", "mixed_rates"), ("c", "advance"), ("d", "clean")]
    ]
    report = summarise(scored, run=RUN, expected=["a", "b", "c", "d"])
    assert [name for name, _ in report.by_tier] == ["clean", "mixed_rates", "advance"]
    assert dict(report.by_tier)["clean"].support == 2 * dict(report.by_tier)["advance"].support
