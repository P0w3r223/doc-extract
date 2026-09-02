"""The five outcomes, and the four ways a naive scorer would get them wrong.

Each test below pins a decision that changes what a published number means: rows are matched by
their printed key rather than by position, a failed extraction is scored rather than dropped, a
correctly-absent field is agreement rather than a hit, and an invented row is counted rather than
overwritten.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from doc_extract.eval.scorer import Outcome, compare, judge
from doc_extract.extract.result import FailureClass


def _outcome(results, field, key=""):
    return next(result.outcome for result in results if result.field == field and result.key == key)


def _by_field(results, field):
    return [result for result in results if result.field == field]


def test_a_perfect_reading_is_correct_or_absent_everywhere(invoice):
    results = compare(invoice, invoice)
    assert {result.outcome for result in results} <= {Outcome.CORRECT, Outcome.ABSENT}
    assert any(result.outcome is Outcome.ABSENT for result in results)


def test_the_four_ways_one_field_can_go(invoice):
    prediction = invoice.model_copy(update={
        "number": "FV/2026/08/0002",   # present on both, different  -> wrong
        "sale_date": None,             # on the document, not read   -> missed
        "payment_account": None,       # on the document, not read   -> missed
    })
    results = compare(invoice, prediction)

    assert _outcome(results, "number") is Outcome.WRONG
    assert _outcome(results, "sale_date") is Outcome.MISSED
    assert _outcome(results, "kind") is Outcome.CORRECT
    #: `discount` is on no line of the fixture, and the prediction says so too.
    assert _outcome(results, "lines[].discount", "1") is Outcome.ABSENT


def test_a_value_the_document_does_not_carry_is_spurious(invoice):
    """The extractor must not compute what is not printed; inventing one is its own outcome."""
    without = invoice.model_copy(update={"sale_date": None})
    results = compare(without, invoice)
    assert _outcome(results, "sale_date") is Outcome.SPURIOUS


def test_rows_are_matched_by_their_number_and_not_by_their_order(invoice):
    """A model that lists the rows backwards has read them; it has not read them wrongly."""
    reversed_lines = invoice.model_copy(update={"lines": tuple(reversed(invoice.lines))})
    results = compare(invoice, reversed_lines)
    assert {result.outcome for result in results} <= {Outcome.CORRECT, Outcome.ABSENT}


def test_rate_blocks_are_matched_by_their_code(invoice):
    swapped = invoice.model_copy(update={"rate_totals": tuple(reversed(invoice.rate_totals))})
    assert {result.outcome for result in compare(invoice, swapped)} <= {
        Outcome.CORRECT, Outcome.ABSENT
    }


def test_a_misread_line_number_is_a_missing_row_and_an_invented_one(invoice):
    """Truer than "the line number was wrong": the row it claims is not the row that is there."""
    renumbered = invoice.lines[0].model_copy(update={"line_no": 9})
    prediction = invoice.model_copy(update={"lines": (renumbered, *invoice.lines[1:])})
    results = _by_field(compare(invoice, prediction), "lines[].net")

    assert _outcome(results, "lines[].net", "1") is Outcome.MISSED
    assert _outcome(results, "lines[].net", "9") is Outcome.SPURIOUS


def test_a_repeated_row_is_counted_as_spurious_rather_than_dropped(invoice):
    doubled = invoice.model_copy(update={"lines": (*invoice.lines, invoice.lines[0])})
    results = compare(invoice, doubled)
    extra = [
        result for result in results
        if result.outcome is Outcome.SPURIOUS and result.field.startswith("lines[]")
    ]
    assert extra, "the second copy of line 1 has to land somewhere"
    assert all(result.gold is None for result in extra)


def test_a_failed_extraction_scores_every_field_as_missed(invoice):
    """Dropping the document instead would compute accuracy over the documents that worked."""
    results = compare(invoice, None)
    assert not [result for result in results if result.outcome is Outcome.SPURIOUS]
    assert {result.outcome for result in results} <= {Outcome.MISSED, Outcome.ABSENT}
    assert _outcome(results, "total_gross") is Outcome.MISSED


def test_gold_with_a_repeated_key_is_refused(invoice):
    """A prediction cannot be matched against an ambiguous key; scoring it would be a coin toss."""
    ambiguous = invoice.model_copy(update={"lines": (invoice.lines[0], invoice.lines[0])})
    with pytest.raises(ValueError, match="repeats a key"):
        compare(ambiguous, invoice)


def test_judge_records_how_the_extraction_ended(invoice):
    score = judge(
        invoice, None,
        doc_id="clean-0000", facets=(("tier", "clean"), ("template", "classic")),
        failure=FailureClass.TRUNCATED,
    )
    assert score.failure is FailureClass.TRUNCATED
    assert score.predicted is False
    assert score.exact is False


def test_exact_means_every_field_including_the_absent_ones(invoice):
    perfect = judge(invoice, invoice, doc_id="d", facets=(("tier", "t"), ("template", "c")),
                    failure=FailureClass.NONE)
    off_by_a_cent = invoice.model_copy(
        update={"total_gross": invoice.total_gross + Decimal("0.01")}
    )
    nearly = judge(invoice, off_by_a_cent, doc_id="d", facets=(("tier", "t"), ("template", "c")),
                   failure=FailureClass.NONE)

    assert perfect.exact is True
    assert nearly.exact is False


def test_judge_will_not_silently_score_a_document_with_no_axes(invoice):
    """`facets` has no default, so forgetting it is a `TypeError` rather than a quiet report.

    It briefly defaulted to `()`. Under that, a caller who omitted it got a report whose per-axis
    tables did not render empty but *vanished* — `report._table` emits nothing for an axis with no
    rows — while every headline rate stayed correct. A well-formed report saying less than it
    claims to is the one failure this project cannot afford.
    """
    with pytest.raises(TypeError):
        judge(invoice, invoice, doc_id="d", failure=FailureClass.NONE)

    explicit = judge(invoice, invoice, doc_id="d", facets=(), failure=FailureClass.NONE)
    assert explicit.facets == (), "a corpus that varies nothing may still say so"
