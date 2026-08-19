"""Per-field confidence, from the two signals this project measured rather than assumed.

`eval/detector.py` and `ground/` each answered half of "is this value right", and the measurements
say exactly how to combine them — which is the only reason this module is shaped the way it is:

* **Grounding is the field-level signal.** Precision 100 %, recall 84.4 %, and zero false alarms
  across 11 652 correctly-read field instances. When it says a value is not on the page, it has
  been right every time it has been asked.
* **An arithmetic violation is a document-level signal that makes a poor field-level accusation.**
  Its `fields` name a *collection* — `lines` — so attributing it to every field of every row scores
  7.4 % precision against 529 false positives. It is kept, because it catches wrong discounts that
  ground perfectly well (the model read a real number out of the wrong column), but it demotes only
  the fields it actually names and never overrides grounding.

**Deterministic, not fitted.** Every rule below is a statement about the signals, and no threshold
was tuned on the corpus it is measured against. The cost is a coarse ordering — four levels, so the
selective-prediction curve has four points rather than a smooth sweep — and that is the honest
shape of the evidence. A weighted score fitted on this corpus would draw a prettier curve and would
be measuring its own training set.

**A field the model did not assert is not assessed.** If the prediction says `null`, grounding has
nothing to look for, and no signal here can tell "correctly absent" from "silently dropped". Those
instances carry no confidence and are excluded from every denominator, which means the curve this
feeds answers *"of the values it gave me, which can I trust"* and not *"did it give me
everything"*. Naming that limit is the point of excluding them rather than scoring them as safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from doc_extract.eval import detector
from doc_extract.ground.resolve import Grounding, Support, resolve
from doc_extract.schema import invariants
from doc_extract.schema.invariants import Severity
from doc_extract.schema.ksef import Invoice
from doc_extract.source.document import SourceDocument


class Confidence(IntEnum):
    """How much of the page backs a value. Ordered, because the curve sorts on it."""

    HIGH = 3
    MEDIUM = 2
    LOW = 1
    NONE = 0


class Route(StrEnum):
    """What to do with a value. The gate this project exists to justify."""

    ACCEPT = "accept"
    REVIEW = "review"
    REJECT = "reject"


#: The route each confidence level takes. Separate from the level itself so that a caller can read
#: the evidence without inheriting this project's opinion of what to do about it — an
#: accounts-payable team that reviews everything below `HIGH` and one that only stops at `NONE` are
#: both reading the same measurement.
ROUTES: dict[Confidence, Route] = {
    Confidence.HIGH: Route.ACCEPT,
    Confidence.MEDIUM: Route.REVIEW,
    Confidence.LOW: Route.REVIEW,
    Confidence.NONE: Route.REJECT,
}


@dataclass(frozen=True, slots=True)
class Assessment:
    """One field instance, and what the page has to say about it."""

    field: str
    key: str
    value: str | None
    #: `None` when the prediction asserted nothing, so there was nothing to check.
    confidence: Confidence | None
    route: Route
    #: Stable tokens naming what drove the verdict, for a report to group by: `ungrounded`,
    #: `partial:0.60`, `rule:lines.net_matches_quantity_times_price`, `document:flagged`.
    reasons: tuple[str, ...] = ()

    @property
    def assessed(self) -> bool:
        return self.confidence is not None


def assess(document: SourceDocument, invoice: Invoice) -> tuple[Assessment, ...]:
    """Judge every field instance of one prediction against the page it claims to come from.

    Takes the source document and the invoice, never the gold: this is the runtime gate, and a gate
    that needed the answer would not be one. `eval/selective.py` is where it meets gold, and only
    to be measured.
    """
    named = _named_fields(invoice)
    flagged = bool(_hard(invoice))
    return tuple(
        _assess(grounding, named=named, flagged=flagged)
        for grounding in resolve(document, invoice)
    )


def _assess(grounding: Grounding, *, named: frozenset[str], flagged: bool) -> Assessment:
    if not grounding.measured:
        return _unassessed(grounding)

    reasons: list[str] = []
    if flagged:
        #: Recorded even when it changes nothing, so a reader can see that the document was flagged
        #: and that this field was not the one accused.
        reasons.append("document:flagged")

    if grounding.support is Support.UNGROUNDED:
        return _at(grounding, Confidence.NONE, [*reasons, "ungrounded"])
    if grounding.support is Support.PARTIAL:
        return _at(grounding, Confidence.LOW, [*reasons, f"partial:{grounding.coverage:.2f}"])

    accusing = sorted(named & {grounding.field})
    if accusing:
        return _at(grounding, Confidence.MEDIUM, [*reasons, f"rule:{grounding.field}"])
    return _at(grounding, Confidence.HIGH, reasons)


def _at(grounding: Grounding, confidence: Confidence, reasons: list[str]) -> Assessment:
    return Assessment(
        field=grounding.field,
        key=grounding.key,
        value=grounding.value,
        confidence=confidence,
        route=ROUTES[confidence],
        reasons=tuple(reasons),
    )


def _unassessed(grounding: Grounding) -> Assessment:
    """A value the page cannot be asked about: absent, or a code it never prints.

    Routed `ACCEPT` and carrying no confidence. The route is not a judgement that the value is
    right — it is that this gate has no grounds to stop it, which is a different claim and the one
    the reasons record.
    """
    return Assessment(
        field=grounding.field,
        key=grounding.key,
        value=grounding.value,
        confidence=None,
        route=Route.ACCEPT,
        reasons=(f"unassessed:{grounding.support}",),
    )


def _hard(invoice: Invoice) -> tuple[invariants.Violation, ...]:
    return tuple(v for v in invariants.check(invoice) if v.severity is Severity.HARD)


def _named_fields(invoice: Invoice) -> frozenset[str]:
    """The scored fields the hard rules point at, expanded from the collections they name."""
    return frozenset(
        name
        for violation in _hard(invoice)
        for part in violation.fields
        for name in detector.covered(part)
    )


def route(assessments: tuple[Assessment, ...]) -> Route:
    """One document's route: the most cautious any of its fields asked for.

    A document is accepted only when every field it asserted was. That is deliberately strict — an
    invoice is paid as a whole, and a single unreadable account number is a reason to stop the
    whole payment rather than to pay it with one field flagged.
    """
    routes = {assessment.route for assessment in assessments}
    if Route.REJECT in routes:
        return Route.REJECT
    return Route.REVIEW if Route.REVIEW in routes else Route.ACCEPT
