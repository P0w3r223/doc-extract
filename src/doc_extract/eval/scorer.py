"""One gold invoice against one prediction, as a list of outcomes. Pure, and total.

No I/O, no configuration, no model. `compare` takes two objects and returns what happened to every
field instance of them — which is the whole of the metric, since every number in the report is a
count of these outcomes.

**Five outcomes, and they partition.** Every field instance that either side carries falls into
exactly one, so a per-field row of the report adds up rather than overlapping:

| | gold has a value | gold has none |
|---|---|---|
| **prediction has a value** | `CORRECT` / `WRONG` | `SPURIOUS` |
| **prediction has none** | `MISSED` | `ABSENT` |

`ABSENT` is agreement, not a non-event. A row with no discount printed and a prediction that says
`null` have agreed about the document, and the count of those agreements is the denominator that
makes detection precision meaningful. It is deliberately not counted as accuracy: a metric that
rewarded correctly-absent fields would rise on documents that carry less.

**A failed extraction is scored, not skipped.** When the pipeline returns no invoice at all, every
gold field is `MISSED` and nothing is spurious. Dropping those documents instead would compute
accuracy over the documents the model happened to answer — the coverage failure the metric rules
exist to prevent, and the one that makes a brittle extractor look precise.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from doc_extract.eval import fields
from doc_extract.eval.fields import Reading, Value
from doc_extract.extract.result import Extraction, FailureClass
from doc_extract.schema.ksef import Invoice


class Outcome(StrEnum):
    """What became of one field instance. Exactly one applies."""

    CORRECT = "correct"
    WRONG = "wrong"
    MISSED = "missed"
    SPURIOUS = "spurious"
    ABSENT = "absent"


#: The outcomes that count as the field having been found at all — the numerator of detection and
#: the denominator of value accuracy.
DETECTED = frozenset({Outcome.CORRECT, Outcome.WRONG})
#: The outcomes a gold value can produce. Their count is the field's support.
SUPPORTED = frozenset({Outcome.CORRECT, Outcome.WRONG, Outcome.MISSED})


@dataclass(frozen=True, slots=True)
class Result:
    """One field instance, judged. Both values are kept, so an error reads without the corpus."""

    field: str
    key: str
    outcome: Outcome
    gold: str | None
    predicted: str | None


@dataclass(frozen=True, slots=True)
class DocumentScore:
    """One document's outcomes, plus the facts about the run that the report groups them by."""

    doc_id: str
    #: The axes the report groups this document by — see `dataset.Case.facets`. Carried as pairs
    #: rather than as two named columns so that a corpus can declare the axes it actually varies.
    facets: tuple[tuple[str, str], ...]
    failure: FailureClass
    predicted: bool
    results: tuple[Result, ...]

    def facet(self, name: str) -> str:
        return dict(self.facets).get(name, "")

    @property
    def tier(self) -> str:
        return self.facet("tier")

    @property
    def template(self) -> str:
        return self.facet("template")

    @property
    def exact(self) -> bool:
        """Every field instance either right or rightly absent. The strictest reading of success."""
        return all(result.outcome in (Outcome.CORRECT, Outcome.ABSENT) for result in self.results)


def compare(gold: Invoice, prediction: Invoice | None) -> tuple[Result, ...]:
    """Every field instance of either invoice, in the order `fields.FIELDS` declares.

    Ordering by field and then by key rather than by document position is what makes two documents'
    result lists comparable line by line — and it is the same discipline as matching by key: the
    order a model emitted its rows in is not information about whether it read them right.
    """
    gold_reading = fields.read(gold)
    _reject_ambiguous_gold(gold_reading)
    predicted_reading = fields.read(prediction) if prediction is not None else _EMPTY

    results = [
        _judge(field.name, key, gold_reading, predicted_reading)
        for field in fields.FIELDS
        for key in _keys(field.name, gold_reading, predicted_reading)
    ]
    results.extend(_spurious_duplicates(predicted_reading))
    return tuple(results)


def judge(
    gold: Invoice,
    prediction: Invoice | None,
    *,
    doc_id: str,
    facets: tuple[tuple[str, str], ...],
    failure: FailureClass,
) -> DocumentScore:
    """One document end to end: the comparison, plus how the extraction itself ended.

    Takes an invoice and a failure class rather than an `Extraction`, so the same function serves a
    run in flight and a prediction file read back off disk. A number in the report is therefore
    computed by the same code whether or not the model was called again.

    **`facets` is required, and deliberately has no default.** It replaced `tier` and `template`,
    which were required too, and briefly carried `()` — under which a caller who forgot it got a
    report whose per-axis tables did not render *empty* but **vanished**, because `_table` returns
    nothing for an axis with no rows. The headline rates stay right and the grouping evidence
    disappears, which on a project whose argument is that figures come from artifacts is the worst
    failure available: a well-formed report that quietly says less than it claims to. A corpus that
    genuinely varies nothing passes `()` and says so.
    """
    return DocumentScore(
        doc_id=doc_id,
        facets=facets,
        failure=failure,
        predicted=prediction is not None,
        results=compare(gold, prediction),
    )


def score(
    gold: Invoice,
    extraction: Extraction,
    *,
    doc_id: str,
    facets: tuple[tuple[str, str], ...],
) -> DocumentScore:
    """`judge`, for a run in flight, taking the failure class off the extraction itself.

    The arguments are named rather than collected as `**where: str`, which had become a lie: every
    pass-through was a `str` when the axes were `tier` and `template`, and `facets` is not one.
    Passing what that annotation invited was a `TypeError`.
    """
    return judge(
        gold,
        extraction.invoice,
        doc_id=doc_id,
        facets=facets,
        failure=extraction.failure,
    )


_EMPTY = Reading(values={}, duplicates=())


def _keys(field: str, gold: Reading, predicted: Reading) -> list[str]:
    """The instances of a field either side carries, gold's first and in its own order.

    A prediction's extra keys follow, so a report reads as "the document's rows, then the invented
    ones" rather than as a sorted merge in which an invented row hides among the real ones.
    """
    keys = [key for (name, key) in gold.values if name == field]
    keys.extend(key for (name, key) in predicted.values if name == field and key not in keys)
    return keys


def _judge(field: str, key: str, gold: Reading, predicted: Reading) -> Result:
    gold_value = gold.get(field, key)
    predicted_value = predicted.get(field, key)

    if gold_value is None and predicted_value is None:
        outcome = Outcome.ABSENT
    elif gold_value is None:
        outcome = Outcome.SPURIOUS
    elif predicted_value is None:
        outcome = Outcome.MISSED
    elif fields.equal(field, gold_value, predicted_value):
        outcome = Outcome.CORRECT
    else:
        outcome = Outcome.WRONG

    return Result(
        field=field,
        key=key,
        outcome=outcome,
        gold=fields.render(gold_value),
        predicted=fields.render(predicted_value),
    )


def _spurious_duplicates(predicted: Reading) -> list[Result]:
    """A repeated row's values, reported rather than dropped.

    A prediction that lists line 3 twice has invented one of them, and the invented one carries
    values that are not on the page. Counting them as spurious is the only reading that keeps the
    outcome table a partition: they are field instances, and every field instance has to land
    somewhere. A duplicate whose value is `None` adds nothing and is left out — it claims nothing.
    """
    return [
        Result(
            field=duplicate.field,
            key=duplicate.key,
            outcome=Outcome.SPURIOUS,
            gold=None,
            predicted=fields.render(duplicate.value),
        )
        for duplicate in predicted.duplicates
        if duplicate.value is not None
    ]


def _reject_ambiguous_gold(reading: Reading) -> None:
    """Gold with a repeated line number or rate code cannot be matched against, so it is refused.

    The corpus cannot produce one — `invariants` has rules for both and `tests/test_synth_build.py`
    requires every generated document to satisfy them. This is here for the held-out set in M7,
    where the gold comes from somewhere this project does not control: silently scoring against an
    ambiguous key would make the metric a coin toss over which of the two rows the prediction was
    compared with.
    """
    if reading.duplicates:
        where = ", ".join(_describe(duplicate) for duplicate in reading.duplicates[:5])
        raise ValueError(
            f"the gold invoice repeats a key, so a prediction cannot be matched against it: {where}"
        )


def _describe(value: Value) -> str:
    return f"{value.field}[{value.key}]"
