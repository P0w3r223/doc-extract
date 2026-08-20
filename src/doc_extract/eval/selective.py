"""The gate, measured: if you accept only what `decide` is confident about, what do you get?

A single accuracy figure describes a system that must answer everything. This project's first pillar
says it should not — a document that breaks its own arithmetic is routed, not returned — and the
honest way to report a system that may decline is a **coverage-accuracy curve**: for each confidence
level, how much of the work it still does, and how right it is on what it kept.

**The curve is cumulative and it is a step function.** `decide` produces four confidence levels
rather than a continuous score, on purpose (see `decide/confidence.py`: a weighted score fitted on
this corpus would draw a smoother curve and would be measuring its own training set). Four levels
give four points, and the reader can see every one of them rather than a line through them.

**Coverage is over values the model asserted, not over the document.** A field the prediction left
`null` has nothing to ground and no signal can tell "correctly absent" from "silently dropped", so
it carries no confidence and sits outside every denominator here. Two consequences, both stated
beside the numbers rather than buried: the curve answers *"of the values it gave me, which can I
trust"*, and a model that answered less would score better on it. `missed` is reported alongside
for exactly that reason — it is the count the curve cannot see.

**Nor is a value on a page with no text to search.** Grounding returns `NO_TEXT` there rather than
`UNGROUNDED`, so a scan's values leave the curve instead of filling it with false alarms. What that
changed is in `Excluded.without_text`: the figure a text-less run reports is now over the values the
pipeline could actually assess, and the count of the ones it could not is printed beside it. The
alternative was measured before it was fixed — on M7e's attacked scans, keeping them in made the
high-confidence bucket *less* accurate than accepting everything.

**The two signals are also measured apart.** Grounding and the arithmetic are reported as their own
field-level detectors before the curve combines them, because they are complements with very
different shapes and a reader who sees only the combination cannot tell which did the work.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from doc_extract.decide.confidence import Assessment, Confidence, assess
from doc_extract.eval import detector
from doc_extract.eval.scorer import Outcome, compare
from doc_extract.ground.resolve import Support
from doc_extract.schema import invariants
from doc_extract.schema.invariants import Severity
from doc_extract.schema.ksef import Invoice
from doc_extract.source.document import SourceDocument

#: Outcomes that mean the asserted value disagrees with the document.
WRONG = frozenset({Outcome.WRONG, Outcome.SPURIOUS})
#: The gold carried a value and the prediction did not. Invisible to every signal here.
MISSED = Outcome.MISSED

#: Highest first, because the curve accepts in that order.
LEVELS: tuple[Confidence, ...] = (
    Confidence.HIGH, Confidence.MEDIUM, Confidence.LOW, Confidence.NONE
)


@dataclass(frozen=True, slots=True)
class Excluded:
    """The ways an asserted or expected value stays out of the curve, counted apart.

    Three different statements, and pooling them would lose the one a reader needs. `missed` is the
    model's silence, `unassessable` is a question grounding declines on principle, and
    `without_text` is a question it could not put because the page had no text. A single "excluded"
    total would make a scanned run look like a talkative model with an odd schema.
    """

    missed: int = 0
    unassessable: int = 0
    without_text: int = 0

    def __add__(self, other: Excluded) -> Excluded:
        return Excluded(
            missed=self.missed + other.missed,
            unassessable=self.unassessable + other.unassessable,
            without_text=self.without_text + other.without_text,
        )


@dataclass(frozen=True, slots=True)
class Judged:
    """One asserted field instance: what the gate thought, and what the gold says."""

    doc_id: str
    field: str
    key: str
    confidence: Confidence
    wrong: bool
    #: Whether each signal flagged this instance, kept apart so either can be scored alone.
    ungrounded: bool
    accused: bool


@dataclass(frozen=True, slots=True)
class Point:
    """One step of the curve: accept everything at this level or above."""

    level: Confidence
    accepted: int
    correct: int
    #: Wrong values that were accepted anyway — the number a reader of a gate actually cares about.
    leaked: int
    total: int

    @property
    def coverage(self) -> float | None:
        return _ratio(self.accepted, self.total)

    @property
    def accuracy(self) -> float | None:
        return _ratio(self.correct, self.accepted)


@dataclass(frozen=True, slots=True)
class Signal:
    """One signal scored on its own, as a field-level detector of a wrong value."""

    name: str
    true_positive: int = 0
    false_positive: int = 0
    false_negative: int = 0
    true_negative: int = 0

    @property
    def precision(self) -> float | None:
        return _ratio(self.true_positive, self.true_positive + self.false_positive)

    @property
    def recall(self) -> float | None:
        return _ratio(self.true_positive, self.true_positive + self.false_negative)


@dataclass(frozen=True, slots=True)
class Curve:
    """A whole run's gate, measured."""

    judged: tuple[Judged, ...]
    points: tuple[Point, ...]
    signals: tuple[Signal, ...]
    #: Gold values the prediction never asserted. Outside the curve, and reported because of it.
    missed: int
    #: Values the prediction *did* assert that grounding declines to ask about — `kind`, and a
    #: non-numeric rate. Outside the curve for the same reason `missed` is, and reported for the
    #: same reason: an exclusion nobody can see is a subset nobody noticed.
    unassessable: int
    #: Documents that produced no invoice at all, so no field of them was ever assessed.
    without_prediction: int
    #: Values the prediction asserted on a page carrying **no text at all**. Grounding answers
    #: `NO_TEXT` rather than `UNGROUNDED`, so they sit outside the curve with `unassessable` rather
    #: than inside it as false alarms — and they are counted apart from it because they mean
    #: something else: not *this is not a question I ask* but *this page gave me nothing to ask
    #: with*. A run where this is most of the corpus has a curve over the remainder, and the report
    #: says which remainder.
    without_text: int = 0

    @property
    def asserted(self) -> int:
        return len(self.judged)

    @property
    def wrong(self) -> int:
        return sum(1 for row in self.judged if row.wrong)


def judge(
    doc_id: str,
    gold: Invoice,
    prediction: Invoice,
    document: SourceDocument,
) -> tuple[tuple[Judged, ...], Excluded]:
    """One document: the gate's verdict on each asserted field, and the values it cannot judge.

    Returns the rows and an `Excluded`. The counts are returned rather than dropped because each is
    an exclusion from the curve's denominator, and an exclusion the report does not print is the
    subset the metric rules exist to forbid.
    """
    assessments = {(a.field, a.key): a for a in assess(document, prediction)}
    named = _named(prediction)
    rows: list[Judged] = []
    missed = unassessable = without_text = 0
    seen: set[tuple[str, str]] = set()

    for result in compare(gold, prediction):
        if result.outcome is MISSED:
            missed += 1
            continue
        identity = (result.field, result.key)
        if identity in seen:
            #: `scorer._spurious_duplicates` emits a repeated row's values under the key it
            #: collides with, while `fields.read` kept only the first — so the assessment here
            #: belongs to a *different* value. Grading an invented row on the real one's grounding
            #: would let a fabricated duplicate inherit its confidence.
            unassessable += 1
            continue
        seen.add(identity)

        assessment = assessments.get(identity)
        if assessment is None or not assessment.assessed:
            #: Split by *why* grounding stayed silent, because the two are different findings: a
            #: page with no text layer excludes every value on it, and pooling that with `kind`
            #: would report a scanner as a schema quirk.
            if assessment is not None and assessment.support is Support.NO_TEXT:
                without_text += 1
            else:
                unassessable += 1
            continue
        rows.append(Judged(
            doc_id=doc_id,
            field=result.field,
            key=result.key,
            confidence=_confidence(assessment),
            wrong=result.outcome in WRONG,
            ungrounded=assessment.suspicious,
            #: Recomputed rather than read off the assessment on purpose: `confidence` attaches a
            #: `rule:` reason only when grounding already said `GROUNDED`, so reading the reasons
            #: would undercount the arithmetic signal precisely where it is the only one talking.
            accused=result.field in named,
        ))
    return tuple(rows), Excluded(
        missed=missed, unassessable=unassessable, without_text=without_text
    )


def _confidence(assessment: Assessment) -> Confidence:
    assert assessment.confidence is not None  # guarded by `assessed`
    return assessment.confidence


def _named(invoice: Invoice) -> frozenset[str]:
    return frozenset(
        name
        for violation in invariants.check(invoice)
        if violation.severity is Severity.HARD
        for part in violation.fields
        for name in detector.covered(part)
    )


def summarise(
    judged: Iterable[Judged],
    *,
    missed: int,
    unassessable: int = 0,
    without_prediction: int,
    without_text: int = 0,
) -> Curve:
    """Rows into a curve and two signal scorecards. Pure: it never re-reads a page."""
    rows = tuple(judged)
    return Curve(
        judged=rows,
        points=_points(rows),
        signals=(
            _signal("grounding", rows, lambda row: row.ungrounded),
            _signal("arithmetic", rows, lambda row: row.accused),
            _signal("either", rows, lambda row: row.ungrounded or row.accused),
        ),
        missed=missed,
        unassessable=unassessable,
        without_prediction=without_prediction,
        without_text=without_text,
    )


def _points(rows: Sequence[Judged]) -> tuple[Point, ...]:
    """One cumulative point per level, highest confidence first."""
    total = len(rows)
    out: list[Point] = []
    accepted = correct = leaked = 0
    for level in LEVELS:
        at_level = [row for row in rows if row.confidence is level]
        accepted += len(at_level)
        correct += sum(1 for row in at_level if not row.wrong)
        leaked += sum(1 for row in at_level if row.wrong)
        out.append(Point(level=level, accepted=accepted, correct=correct,
                         leaked=leaked, total=total))
    return tuple(out)


def _signal(name: str, rows: Sequence[Judged], flags) -> Signal:
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for row in rows:
        flagged = flags(row)
        counts["tp" if (row.wrong and flagged) else
               "fp" if flagged else
               "fn" if row.wrong else "tn"] += 1
    return Signal(
        name=name,
        true_positive=counts["tp"],
        false_positive=counts["fp"],
        false_negative=counts["fn"],
        true_negative=counts["tn"],
    )


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator
