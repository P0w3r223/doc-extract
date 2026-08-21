"""Per-field confidence, from the three signals this project measured rather than assumed.

`eval/detector.py` and `ground/` each answered part of "is this value right", and the measurements
say exactly how to combine them — which is the only reason this module is shaped the way it is:

* **Grounding is the field-level signal.** Precision 100 %, recall 85.7 %, and zero false alarms
  across 11 652 correctly-read field instances. When it says a value is not on the page, it has
  been right every time it has been asked — on all 24 committed runs, not one false positive.
* **An arithmetic violation is a document-level signal that makes a poor field-level accusation.**
  Its `fields` name a *collection* — `lines` — so attributing it to every field of every row scores
  7.4 % precision against 529 false positives. It is kept, because it catches wrong discounts that
  ground perfectly well (the model read a real number out of the wrong column), but it demotes only
  the fields it actually names and never overrides grounding.
* **A contention names two fields and one of them is wrong.** `ground/joint.py` asks whether a
  reading's grounded values can each be given a place of their own on the page; when two of them
  claim one printed figure, both are flagged, because no label-free fact says which is the intruder.
  Precision is therefore about a half by construction — six times the arithmetic's field-level
  figure and nowhere near grounding's — so it demotes on the same terms as a hard rule and for the
  same reason.

**Two demotions do not stack.** A value that is both contended and named by a hard rule falls one
level, not two. They are two ways of noticing one kind of failure — a real figure read into the
wrong field — and compounding them would let the coarser signal borrow the finer one's confidence.

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

**Nor is a field on a page this pipeline cannot read.** `Support.NO_TEXT` is the verdict M7e forced:
a scan with no text layer gave grounding nothing to search, it answered `UNGROUNDED` anyway, and
this module could not tell that from a value genuinely missing from the page. The consequence was
not noise but inversion — the values that *could* ground were the ones on the rung an injected
instruction survives, so the gate sorted the attacked-and-obeyed values into `HIGH` and
auto-accepting only that bucket scored **worse than accepting everything**. Such a value now carries
no confidence either, and it is routed `REVIEW` rather than `ACCEPT`: an absent value and a
non-printed code are questions that did not arise, while this one arose and could not be put. A gate
that auto-accepted what it had failed to check would be reporting an instrument's absence as its
verdict.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from doc_extract.eval import detector
from doc_extract.ground import joint
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
    #: What grounding said, carried structurally rather than left to be parsed back out of
    #: `reasons`. A consumer that recovered the signal by prefix-matching prose would go silently
    #: all-negative the day a token is renamed, and a measurement failure that looks like a
    #: finding is the worst kind.
    support: Support = Support.ABSENT
    #: Whether this reading had to share a place on the page with another of its own. Carried
    #: structurally for the same reason `support` is: `eval/selective.py` scores the signal on its
    #: own, and recovering it by prefix-matching `reasons` would go silently all-negative the day a
    #: token is renamed.
    contended: bool = False
    #: Stable tokens naming what drove the verdict, for a report to group by: `ungrounded`,
    #: `partial:0.60`, `contended`, `rule:lines.net_matches_quantity_times_price`,
    #: `document:flagged`.
    reasons: tuple[str, ...] = ()

    @property
    def assessed(self) -> bool:
        return self.confidence is not None

    @property
    def suspicious(self) -> bool:
        """Whether **grounding** doubted this value. Not the same as a low confidence: a field a
        hard rule accuses is demoted without grounding having said anything against it."""
        return self.support in (Support.UNGROUNDED, Support.PARTIAL)


def assess(document: SourceDocument, invoice: Invoice) -> tuple[Assessment, ...]:
    """Judge every field instance of one prediction against the page it claims to come from.

    Takes the source document and the invoice, never the gold: this is the runtime gate, and a gate
    that needed the answer would not be one. `eval/selective.py` is where it meets gold, and only
    to be measured.
    """
    named = _named_fields(invoice)
    flagged = bool(_hard(invoice))
    groundings = resolve(document, invoice)
    contested = joint.contended(groundings)
    return tuple(
        _assess(grounding, named=named, flagged=flagged, contested=contested)
        for grounding in groundings
    )


def _assess(
    grounding: Grounding,
    *,
    named: frozenset[str],
    flagged: bool,
    contested: frozenset[tuple[str, str]],
) -> Assessment:
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

    #: Both remaining signals demote by one step and neither decides, so a value carrying both is
    #: demoted once rather than twice. That is deliberate: they are two ways of noticing the same
    #: kind of failure — a real figure read into the wrong field — and a value the arithmetic
    #: already accuses is not made more doubtful by the page also being short of places for it.
    if (grounding.field, grounding.key) in contested:
        return _at(grounding, Confidence.MEDIUM, [*reasons, "contended"], contended=True)
    if grounding.field in named:
        return _at(grounding, Confidence.MEDIUM, [*reasons, f"rule:{grounding.field}"])
    return _at(grounding, Confidence.HIGH, reasons)


def _at(
    grounding: Grounding,
    confidence: Confidence,
    reasons: list[str],
    *,
    contended: bool = False,
) -> Assessment:
    return Assessment(
        field=grounding.field,
        key=grounding.key,
        value=grounding.value,
        confidence=confidence,
        route=ROUTES[confidence],
        support=grounding.support,
        contended=contended,
        reasons=tuple(reasons),
    )


#: What to do with a value that carries no confidence, by the reason it carries none. The two kinds
#: are not the same claim and must not share a route. `ABSENT` and `NOT_PRINTED` are questions that
#: never arose — the invoice has no discount, the page never prints an FA(3) code — and this gate
#: has no grounds to stop them. `NO_TEXT` is a question that arose and could not be put, and
#: accepting it would report the absence of an instrument as a clean reading.
UNASSESSED_ROUTES: dict[Support, Route] = {
    Support.ABSENT: Route.ACCEPT,
    Support.NOT_PRINTED: Route.ACCEPT,
    Support.NO_TEXT: Route.REVIEW,
}


def _unassessed(grounding: Grounding) -> Assessment:
    """A value grounding did not judge: absent, a code the page never prints, or no page text.

    Carries no confidence in every case, so none of these reaches the curve. The route differs, and
    `UNASSESSED_ROUTES` carries why: neither route is a judgement that the value is right, and the
    reason token records which of the three verdicts produced it.
    """
    return Assessment(
        field=grounding.field,
        key=grounding.key,
        value=grounding.value,
        confidence=None,
        route=UNASSESSED_ROUTES[grounding.support],
        support=grounding.support,
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
