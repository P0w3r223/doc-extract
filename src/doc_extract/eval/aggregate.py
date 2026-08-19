"""Outcomes into counts, and counts into rates that refuse to exist without a denominator.

Every metric here is `float | None`, and the `None` is the point. A field the corpus never carries
has no accuracy; a run that predicted nothing has no precision. Returning `0.0` for either would put
a number in the table that reads as a measurement and is not one — the failure mode the metric rules
call "a metric that is a hardcoded value", arriving by the back door of an empty denominator.

**Three rates, because they answer three questions.** Detection recall asks whether the field was
found at all; detection precision asks whether what was produced was on the document; value accuracy
asks whether a found field was read correctly. `accuracy` is the end-to-end product of the first and
the third, and it is reported alongside them rather than instead of them: a field with 50 % accuracy
because it is half missed needs different work from one that is half misread.

**Coverage is checked, not assumed.** `summarise` is given the documents the corpus manifest
attests to and refuses to report on a different set unless the caller says a subset is intended —
and then the report says so too, so a partial run cannot be read as a whole one later.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from doc_extract.eval import fields
from doc_extract.eval.predictions import Prediction, RunMeta
from doc_extract.eval.scorer import DETECTED, SUPPORTED, DocumentScore, Outcome, Result
from doc_extract.extract.client import Usage


class CoverageError(RuntimeError):
    """The documents scored are not the documents the corpus attests to."""


@dataclass(frozen=True, slots=True)
class Tally:
    """Counts of the five outcomes, and the rates that follow from them."""

    correct: int = 0
    wrong: int = 0
    missed: int = 0
    spurious: int = 0
    absent: int = 0

    def __add__(self, other: Tally) -> Tally:
        return Tally(
            correct=self.correct + other.correct,
            wrong=self.wrong + other.wrong,
            missed=self.missed + other.missed,
            spurious=self.spurious + other.spurious,
            absent=self.absent + other.absent,
        )

    @property
    def support(self) -> int:
        """Field instances the gold carries. Every per-field row of the report states it."""
        return self.correct + self.wrong + self.missed

    @property
    def detected(self) -> int:
        return self.correct + self.wrong

    @property
    def produced(self) -> int:
        """Field instances the prediction carries, right, wrong or invented."""
        return self.correct + self.wrong + self.spurious

    @property
    def instances(self) -> int:
        return self.support + self.spurious + self.absent

    @property
    def detection_recall(self) -> float | None:
        """Of the values on the document, how many the prediction offered a value for."""
        return _ratio(self.detected, self.support)

    @property
    def detection_precision(self) -> float | None:
        """Of the values the prediction offered, how many the document actually carries."""
        return _ratio(self.detected, self.produced)

    @property
    def value_accuracy(self) -> float | None:
        """Of the values it found, how many it read correctly."""
        return _ratio(self.correct, self.detected)

    @property
    def accuracy(self) -> float | None:
        """Of the values on the document, how many came back right — detection and reading."""
        return _ratio(self.correct, self.support)


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def tally(results: Iterable[Result]) -> Tally:
    counts = Counter(result.outcome for result in results)
    return Tally(
        correct=counts[Outcome.CORRECT],
        wrong=counts[Outcome.WRONG],
        missed=counts[Outcome.MISSED],
        spurious=counts[Outcome.SPURIOUS],
        absent=counts[Outcome.ABSENT],
    )


@dataclass(frozen=True, slots=True)
class Coverage:
    """Which documents were scored against which documents were supposed to be."""

    expected: tuple[str, ...]
    scored: tuple[str, ...]

    @property
    def missing(self) -> tuple[str, ...]:
        scored = set(self.scored)
        return tuple(doc_id for doc_id in self.expected if doc_id not in scored)

    @property
    def unexpected(self) -> tuple[str, ...]:
        expected = set(self.expected)
        return tuple(doc_id for doc_id in self.scored if doc_id not in expected)

    @property
    def complete(self) -> bool:
        return not self.missing and not self.unexpected

    @property
    def ratio(self) -> float | None:
        return _ratio(len(self.scored) - len(self.unexpected), len(self.expected))


@dataclass(frozen=True, slots=True)
class Scored:
    """One document's prediction and its judgement, kept together so the report can cross them."""

    prediction: Prediction
    score: DocumentScore


@dataclass(frozen=True, slots=True)
class Report:
    """Everything the run measured, as counts. Rendering it is `report.py`'s job, not this one's."""

    run: RunMeta
    coverage: Coverage
    documents: int
    #: Documents that produced a well-formed `Invoice` at all — not documents that produced a
    #: *correct* one, which is `exact`.
    extracted: int
    exact: int
    overall: Tally
    by_field: tuple[tuple[str, Tally], ...]
    by_group: tuple[tuple[str, Tally], ...]
    by_tier: tuple[tuple[str, Tally], ...]
    by_template: tuple[tuple[str, Tally], ...]
    failures: tuple[tuple[str, int], ...]
    stop_reasons: tuple[tuple[str, int], ...]
    usage: Usage
    attempts: int
    repairs: int

    @property
    def unsupported_fields(self) -> tuple[str, ...]:
        """Declared fields the corpus never carries.

        Not an error — `discount` is absent from most documents by design, and a held-out set may
        legitimately lack a field. It is printed in the report because a field with no support is
        also what "the extractor was never asked for it" looks like from here, and the two are worth
        telling apart before a table of dashes is read as coverage.
        """
        return tuple(name for name, counts in self.by_field if counts.support == 0)


def summarise(
    scored: Sequence[Scored],
    *,
    run: RunMeta,
    expected: Sequence[str],
    allow_partial: bool = False,
) -> Report:
    """Counts over a whole run, after checking it is the run it claims to be."""
    scored_ids = tuple(item.score.doc_id for item in scored)
    coverage = Coverage(expected=tuple(expected), scored=scored_ids)
    if not coverage.complete and not allow_partial:
        raise CoverageError(coverage_message(coverage))

    results = [result for item in scored for result in item.score.results]
    by_field = tuple(
        (field.name, tally(result for result in results if result.field == field.name))
        for field in fields.FIELDS
    )
    by_group = tuple(
        (str(group), tally(
            result for result in results if fields.BY_NAME[result.field].group is group
        ))
        for group in _ordered_groups()
    )

    return Report(
        run=run,
        coverage=coverage,
        documents=len(scored),
        extracted=sum(1 for item in scored if item.score.predicted),
        exact=sum(1 for item in scored if item.score.exact),
        overall=tally(results),
        by_field=by_field,
        by_group=by_group,
        by_tier=_grouped(scored, lambda item: item.score.tier),
        by_template=_grouped(scored, lambda item: item.score.template),
        failures=_counted(item.prediction.failure for item in scored),
        stop_reasons=_counted(item.prediction.stop_reason for item in scored),
        usage=sum((item.prediction.usage for item in scored), Usage()),
        attempts=sum(len(item.prediction.attempts) for item in scored),
        repairs=sum(item.prediction.repairs for item in scored),
    )


def _ordered_groups() -> tuple[fields.Group, ...]:
    """The groups in the order the fields declare them, so the report follows the document."""
    seen: list[fields.Group] = []
    for field in fields.FIELDS:
        if field.group not in seen:
            seen.append(field.group)
    return tuple(seen)


def _grouped(scored: Sequence[Scored], key) -> tuple[tuple[str, Tally], ...]:
    """Tallies by some property of the document, in order of first appearance.

    First appearance rather than alphabetical: the corpus manifest's order is the tier order the
    generator declares, which is the order a reader of `tiers.py` expects — and sorting would put
    `advance` before the `clean` control arm every other tier is read against.
    """
    order: list[str] = []
    buckets: dict[str, list[Result]] = {}
    for item in scored:
        name = key(item)
        if name not in buckets:
            order.append(name)
            buckets[name] = []
        buckets[name].extend(item.score.results)
    return tuple((name, tally(buckets[name])) for name in order)


def _counted(values: Iterable[str]) -> tuple[tuple[str, int], ...]:
    """A count per value, most frequent first, ties broken by name so the output is stable."""
    counts = Counter(values)
    return tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def coverage_message(coverage: Coverage) -> str:
    missing, unexpected = coverage.missing, coverage.unexpected
    parts = [
        f"scored {len(coverage.scored)} of the {len(coverage.expected)} documents the corpus "
        "manifest attests to"
    ]
    if missing:
        parts.append(f"missing: {_first(missing)}")
    if unexpected:
        parts.append(f"not in the manifest: {_first(unexpected)}")
    parts.append(
        "pass allow_partial=True (or --allow-partial) to report on a subset deliberately; the "
        "report will record that it is one"
    )
    return "; ".join(parts)


def _first(ids: tuple[str, ...], limit: int = 5) -> str:
    shown = ", ".join(ids[:limit])
    return shown if len(ids) <= limit else f"{shown}, ... and {len(ids) - limit} more"


#: Outcome sets `report.py` and the tests read, re-exported so a caller does not reach into
#: `scorer` for them.
__all__ = [
    "DETECTED",
    "SUPPORTED",
    "Coverage",
    "CoverageError",
    "Report",
    "Scored",
    "Tally",
    "coverage_message",
    "summarise",
    "tally",
]
