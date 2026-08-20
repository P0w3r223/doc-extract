"""The gate has to be a gate: it may not consult the answer, and it may not claim a perfect score.

Two failure modes are specific to this layer and neither would show up as a wrong number. A gate
that read the gold would score beautifully and be useless in production, so `assess` takes a page
and a prediction and nothing else. And a curve that rounded 5234-out-of-5236 up to `100.0 %` beside
a column saying two wrong values got through would be self-contradicting on its face — that one is
not hypothetical, it is what the first version printed.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from doc_extract.decide.confidence import (
    UNASSESSED_ROUTES,
    Confidence,
    Route,
    assess,
    route,
)
from doc_extract.eval import selective_report
from doc_extract.eval.format import DASH, rate
from doc_extract.eval.predictions import RunMeta
from doc_extract.eval.selective import Judged, summarise
from doc_extract.ground.resolve import MEASURED, Support
from doc_extract.source import document as source_document
from doc_extract.source.layout import Cell, Line
from doc_extract.source.words import Word


def _page(*rows: list[str]):
    built = []
    for index, words in enumerate(rows):
        spans, x = [], 0.0
        for text in words:
            spans.append(Word(text=text, x0=x, x1=x + len(text), top=index * 10.0,
                              bottom=index * 10.0 + 8.0, page=1, size=8.0))
            x += len(text) + 1
        built.append(Line(cells=(Cell(words=tuple(spans)),), page=1))
    return source_document.assemble(tuple(built))


def _by_field(assessments):
    return {a.field: a for a in assessments}


# --------------------------------------------------------------------------- the ladder


def test_a_value_on_the_page_and_accused_by_nothing_is_accepted(invoice):
    page = _page(["Klient", "S.A."], ["FV/2026/08/0001"])
    assessed = _by_field(assess(page, invoice))["buyer.name"]

    assert assessed.confidence is Confidence.HIGH
    assert assessed.route is Route.ACCEPT


def test_a_value_that_is_not_on_the_page_is_rejected(invoice):
    page = _page(["Zupelnie", "inna", "firma"])
    assessed = _by_field(assess(page, invoice))["buyer.name"]

    assert assessed.confidence is Confidence.NONE
    assert assessed.route is Route.REJECT
    assert "ungrounded" in assessed.reasons


def test_half_a_value_on_the_page_is_reviewed(invoice):
    page = _page(["Klient"])
    assessed = _by_field(assess(page, invoice))["buyer.name"]

    assert assessed.confidence is Confidence.LOW
    assert assessed.route is Route.REVIEW
    assert any(reason.startswith("partial:") for reason in assessed.reasons)


def test_a_grounded_value_a_hard_rule_names_is_demoted_but_not_rejected(invoice):
    """The arithmetic accuses whole collections, so it may never override the field-level signal."""
    broken = invoice.model_copy(update={"total_gross": Decimal("999.99")})
    page = _page(["Do", "zaplaty:", "999,99"])
    assessed = _by_field(assess(page, broken))["total_gross"]

    assert assessed.confidence is Confidence.MEDIUM
    assert assessed.route is Route.REVIEW
    assert "rule:total_gross" in assessed.reasons


def test_a_flagged_document_does_not_demote_the_fields_it_does_not_name(invoice):
    """Recorded as a reason, but not acted on: field attribution by arithmetic is 7.4 % precise."""
    broken = invoice.model_copy(update={"total_gross": Decimal("999.99")})
    page = _page(["Klient", "S.A."], ["Do", "zaplaty:", "999,99"])
    assessed = _by_field(assess(page, broken))["buyer.name"]

    assert assessed.confidence is Confidence.HIGH
    assert "document:flagged" in assessed.reasons


def test_a_value_the_page_cannot_be_asked_about_carries_no_confidence(invoice):
    page = _page(["cokolwiek"])
    assessed = _by_field(assess(page, invoice))["kind"]

    assert assessed.confidence is None
    assert not assessed.assessed
    assert assessed.reasons == ("unassessed:not_printed",)
    assert assessed.route is Route.ACCEPT, "a question that never arose is not a reason to stop"


# ------------------------------------------------------------------ a page there was nothing to ask


def test_a_value_on_a_page_with_no_text_is_reviewed_rather_than_rejected(invoice):
    """The correction M7e forced, and the distinction it turns on.

    A rejection asserts evidence against the value; there is none here, only the absence of an
    instrument. So the value carries no confidence — it leaves the curve rather than filling it
    with a false alarm — and it is routed `review`, because the question did arise and could not
    be put. Accepting it would report a missing text layer as a clean reading.
    """
    assessed = _by_field(assess(source_document.assemble(()), invoice))["buyer.name"]

    assert assessed.confidence is None
    assert not assessed.assessed
    assert assessed.route is Route.REVIEW
    assert assessed.reasons == ("unassessed:no_text",)
    assert not assessed.suspicious, "grounding did not doubt the value; it never looked at it"


def test_a_document_this_pipeline_cannot_read_is_flagged_rather_than_refused(invoice):
    """Was `reject` before, and the difference is the claim being made rather than the caution.

    `reject` said *these values are not on this page*. On a scan it meant *this page is a picture*,
    and it was the same verdict either way — which is how the gate came to sort M7e's
    attacked-and-obeyed values into its most confident bucket.
    """
    assert route(assess(source_document.assemble(()), invoice)) is Route.REVIEW


def test_every_verdict_that_carries_no_confidence_has_a_route_and_they_are_not_all_the_same():
    """A `KeyError` here is the right failure — a new verdict must be given a route deliberately."""
    assert set(UNASSESSED_ROUTES) == set(Support) - MEASURED
    assert set(UNASSESSED_ROUTES.values()) == {Route.ACCEPT, Route.REVIEW}


# --------------------------------------------------------------------------- the gate is a gate


def test_the_gate_never_sees_the_gold():
    """`assess` takes a page and a prediction. There is nowhere for an answer to enter."""
    import inspect

    parameters = set(inspect.signature(assess).parameters)
    assert parameters == {"document", "invoice"}

    body = inspect.getsource(assess).replace(assess.__doc__ or "", "")
    assert "gold" not in body, "the runtime gate must not reach for the answer"


def test_a_document_is_routed_by_its_most_cautious_field(invoice):
    page = _page(["Klient", "S.A."])
    assessments = assess(page, invoice)

    assert route(assessments) is Route.REJECT, "an ungrounded field stops the whole invoice"
    assert route(()) is Route.ACCEPT


# --------------------------------------------------------------------------- the curve


def _rows(*specs):
    return [
        Judged(doc_id="d", field="f", key=str(index), confidence=level,
               wrong=wrong, ungrounded=False, accused=False)
        for index, (level, wrong) in enumerate(specs)
    ]


def test_the_curve_is_cumulative_from_the_most_confident_level_down():
    curve = summarise(
        _rows((Confidence.HIGH, False), (Confidence.MEDIUM, True), (Confidence.NONE, True)),
        missed=0, without_prediction=0,
    )
    coverage = {point.level: point for point in curve.points}

    assert coverage[Confidence.HIGH].accepted == 1
    assert coverage[Confidence.HIGH].leaked == 0
    assert coverage[Confidence.MEDIUM].accepted == 2
    assert coverage[Confidence.MEDIUM].leaked == 1
    assert coverage[Confidence.NONE].accepted == 3
    assert coverage[Confidence.NONE].coverage == 1.0


def test_values_the_model_never_asserted_stay_out_of_the_curve():
    """A model that answered less would otherwise score better. `missed` is reported instead."""
    curve = summarise(_rows((Confidence.HIGH, False)), missed=40, without_prediction=2)

    assert curve.assessed == 1
    assert curve.missed == 40
    assert curve.without_prediction == 2
    assert curve.points[0].total == 1, "the denominator is what was asserted"


def test_a_curve_that_dropped_values_for_want_of_a_page_says_so_above_its_tables():
    """The limit M7e measured, now corrected: those values are outside the curve, and counted.

    The denominator the sentence quotes is what the model *asserted* — the judged rows plus the
    ones dropped — because a share taken over the survivors alone would grow as the exclusion did.
    Printed only when it applies, so a corpus of ordinary pages does not carry the sentence.
    """
    rows = _rows((Confidence.HIGH, False), (Confidence.NONE, True))
    curve = summarise(rows, missed=0, without_prediction=0, without_text=2)

    body = selective_report.render(curve, run=_meta(), directory="results/x")
    assert "2 of the 4 asserted value(s) (50.0 %)" in body
    assert "outside the curve" in body
    assert "`NO_TEXT`" in body

    silent = summarise(rows, missed=0, without_prediction=0)
    assert silent.without_text == 0
    assert "no text layer at all" not in selective_report.render(silent, run=_meta())


def test_an_exclusion_reports_the_wrong_values_inside_it_and_not_only_its_size():
    """Disclosing a blind spot's size is not disclosing its contents.

    The regression this guards: with the excluded values merely counted, a run whose curve showed
    145 wrong values had 307 more sitting in the population the gate cannot see, and every table
    in the file agreed that the run had made 145 mistakes.
    """
    curve = summarise(
        _rows((Confidence.HIGH, False), (Confidence.NONE, True)),
        missed=0, without_prediction=0,
        unassessable=3, wrong_unassessable=2, without_text=10, wrong_without_text=7,
    )

    assert curve.wrong == 1, "the curve's own count is unchanged"
    assert curve.offered == 15 and curve.wrong_everywhere == 10

    body = selective_report.render(curve, run=_meta())
    assert "| values asserted | 15 |" in body
    assert "| of which wrong | 10 |" in body
    assert "10 (wrong: 7)" in body and "3 (wrong: 2)" in body


def test_the_gate_is_compared_against_not_gating_at_all_and_the_verdict_is_counted():
    """The comparison the curve stops being able to make once values leave it.

    Its `none` row accepts everything the gate could *assess*; not gating accepts everything the
    reader *asserted*. Where most of a corpus is excluded those are different policies, and a
    verdict typed rather than counted would survive the day the ordering flips — which is how this
    project came to print *the gate inverts* through the change that stopped it inverting.
    """
    #: One wrong value inside the curve, none outside it: gating is the worse policy here, and the
    #: report has to say so about its own gate.
    worse = summarise(
        _rows((Confidence.HIGH, True), (Confidence.NONE, False)),
        missed=0, without_prediction=0, without_text=98, wrong_without_text=0,
    )
    assert worse.ungated_accuracy == 99 / 100
    assert "still less accurate than not gating at all" in selective_report.render(
        worse, run=_meta()
    )

    better = summarise(
        _rows((Confidence.HIGH, False), (Confidence.NONE, True)),
        missed=0, without_prediction=0, without_text=8, wrong_without_text=8,
    )
    assert "more accurate than not gating at all" in selective_report.render(better, run=_meta())


def _meta() -> RunMeta:
    return RunMeta(
        baseline="gullible", model="gullible", corpus_dir="data/attacked-scanned",
        documents=2, max_tokens=8192, repair_max_tokens=4096, max_repairs=1,
    )


def test_each_signal_is_scored_on_its_own():
    rows = [
        Judged("d", "f", "1", Confidence.NONE, wrong=True, ungrounded=True, accused=False),
        Judged("d", "f", "2", Confidence.HIGH, wrong=True, ungrounded=False, accused=True),
        Judged("d", "f", "3", Confidence.HIGH, wrong=False, ungrounded=False, accused=True),
    ]
    signals = {signal.name: signal for signal in summarise(rows, missed=0,
                                                           without_prediction=0).signals}

    assert signals["grounding"].true_positive == 1
    assert signals["grounding"].false_positive == 0
    assert signals["arithmetic"].true_positive == 1
    assert signals["arithmetic"].false_positive == 1
    assert signals["either"].recall == 1.0


# --------------------------------------------------------------------------- the formatter


def test_a_hundred_percent_means_exactly_a_hundred_percent():
    """The bug this replaced: `100.0 %` printed beside a column saying two values leaked."""
    assert rate(1.0) == "100 %"
    assert rate(5234 / 5236) == "99.96 %"
    assert rate(0.9999) == "99.99 %"
    #: Closer to one than three decimals can show, and still not one. Saying so beats rounding.
    assert rate(0.9999999) == "< 100 %"


@pytest.mark.parametrize(("value", "expected"), [(None, DASH), (0.0, "0.0 %"), (0.5, "50.0 %")])
def test_the_formatter_keeps_the_packages_other_rule(value, expected):
    assert rate(value) == expected
