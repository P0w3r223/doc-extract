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

from doc_extract.decide.confidence import Confidence, Route, assess, route
from doc_extract.eval.format import DASH, rate
from doc_extract.eval.selective import Judged, summarise
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

    assert curve.asserted == 1
    assert curve.missed == 40
    assert curve.without_prediction == 2
    assert curve.points[0].total == 1, "the denominator is what was asserted"


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
