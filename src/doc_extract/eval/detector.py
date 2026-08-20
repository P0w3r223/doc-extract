"""The validator measured as a detector. The project's headline, and where a negative result lands.

Every other module under `eval` asks how well a document was read. This one asks the question the
project exists for: does **"the arithmetic holds" predict "the fields are right"**?

An invoice carries redundancy its issuer already reconciled — net + VAT = gross, rows sum to their
rate block, a rate applied to a net gives that block's VAT, check digits on the NIP and the IBAN.
`schema.invariants` turns that redundancy into violations. Nothing about the redundancy guarantees
that those violations *predict extraction error*, and nothing in this package assumes it. It is
measured here, as a binary classifier, against gold.

**The detector's positive class is the document, not the field.** A hard rule is a statement about a
relationship between several fields: `P_15` disagreeing with the rate totals says one of the two is
wrong without saying which. That coarseness is not an apology — a routing gate is a per-document
decision, and "send this invoice to a human" is the action the measurement is for. How much of the
blame a rule can pin on an individual field is measured separately, as `localisation` below, because
it is a weaker claim and would flatter the headline if folded into it.

**Hard and heuristic are two detectors, never one.** They are reported separately and never summed,
for the reason `invariants` gives: a heuristic's lawful exceptions would be indistinguishable from a
real arithmetic miss, so pooling them lets rules with known false positives borrow the precision of
rules that have none.

**A document with no prediction is outside the detector's domain.** When extraction returned no
invoice there is nothing for a rule to read, so the document is neither a catch nor a miss. Those
are counted as their own verdict and excluded from every denominator, with the exclusion printed
beside the rates. Counting them as caught would credit the invariants with a refusal the pipeline
had already made on its own — the most flattering available reading, and the least true one.

**The blind spot is the finding.** `eval.corrupt.INVISIBLE_KINDS` names two error kinds no rule at
either severity can see, and the per-kind table exists to print their zero. A study reporting only
the detectable kinds would have measured its own corruption set rather than the detector.

`corrupt.CAUGHT_BY` extends that from a set to a mapping, because with both severities reported each
table necessarily contains rows the *other* one owns. A row a study was never asked to catch is
labelled as such rather than left to read as a miss — otherwise the heuristic half would report a
recall near zero for the arithmetic kinds it was never meant to see, which is the same mistake as
pooling the two severities, made in the other direction.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from doc_extract.eval import corrupt, fields
from doc_extract.eval.scorer import DocumentScore, Outcome
from doc_extract.schema import invariants
from doc_extract.schema.invariants import Severity
from doc_extract.schema.ksef import Invoice

#: The outcomes that mean the prediction disagrees with the document. `CORRECT` and `ABSENT` are
#: both agreement — see `scorer`, where an absent value the gold also lacks is a reading of the page
#: rather than a non-event. A detector that fired on those would be flagging correct documents.
DISAGREEMENT = frozenset({Outcome.WRONG, Outcome.MISSED, Outcome.SPURIOUS})


class Verdict(StrEnum):
    """What one document was, as a detection problem. Exactly one applies, and they partition."""

    TRUE_POSITIVE = "true_positive"
    FALSE_POSITIVE = "false_positive"
    FALSE_NEGATIVE = "false_negative"
    TRUE_NEGATIVE = "true_negative"
    #: Extraction produced no invoice, so no rule could read one. Not a miss — no input.
    NO_PREDICTION = "no_prediction"


FIRED = frozenset({Verdict.TRUE_POSITIVE, Verdict.FALSE_POSITIVE})
WRONG = frozenset({Verdict.TRUE_POSITIVE, Verdict.FALSE_NEGATIVE})
#: The verdicts a rate may be computed over: the detector had an invoice and gold had an opinion.
JUDGED = frozenset(Verdict) - {Verdict.NO_PREDICTION}


@dataclass(frozen=True, slots=True)
class DocumentVerdict:
    """One document's two opinions of itself: what the rules said, and what the gold says."""

    doc_id: str
    tier: str
    verdict: Verdict
    #: The rule ids that fired, deduplicated, in `invariants`' own order.
    rules: tuple[str, ...] = ()
    #: The distinct scored fields the gold comparison found fault with — what a detector *should*
    #: have pointed at. Kept on the verdict so a false negative reads without re-running the scorer.
    wrong_fields: tuple[str, ...] = ()
    #: The scored fields the fired rules name, via `covered`. Empty when nothing fired.
    named_fields: tuple[str, ...] = ()
    #: The corruption kinds recorded on the prediction, for runs that inject known errors.
    injected: tuple[str, ...] = ()

    @property
    def fired(self) -> bool:
        return self.verdict in FIRED

    @property
    def wrong(self) -> bool:
        return self.verdict in WRONG

    @property
    def localised(self) -> bool | None:
        """Whether a true positive pointed at a field that is genuinely wrong.

        `None` for every verdict but a true positive, because the question is only meaningful when
        there was both something to find and something that fired. A false positive names fields on
        a document where nothing is wrong, so there is no right answer for it to have hit.
        """
        if self.verdict is not Verdict.TRUE_POSITIVE:
            return None
        return bool(set(self.named_fields) & set(self.wrong_fields))


def verdict(
    score: DocumentScore,
    invoice: Invoice | None,
    *,
    severity: Severity = Severity.HARD,
    notes: Sequence[str] = (),
) -> DocumentVerdict:
    """Judge one document as a detection problem.

    Takes the scored document and the predicted invoice rather than an `Extraction`, for the same
    reason `scorer.judge` does: a number in this study is computed by the same code whether it came
    from a run in flight or from a prediction file read back off disk, without the model.

    The invariants are run on the **prediction**, never on the gold. That is the whole design — the
    signal has to be available at inference time on a document nobody annotated, and a check that
    needed the gold would be a scorer wearing a detector's name.
    """
    wrong_fields = _wrong_fields(score)
    if invoice is None:
        return DocumentVerdict(
            doc_id=score.doc_id,
            tier=score.tier,
            verdict=Verdict.NO_PREDICTION,
            wrong_fields=wrong_fields,
            injected=kinds(notes),
        )

    rules = _fired(invoice, severity)
    is_wrong = bool(wrong_fields)
    match (bool(rules), is_wrong):
        case (True, True):
            outcome = Verdict.TRUE_POSITIVE
        case (True, False):
            outcome = Verdict.FALSE_POSITIVE
        case (False, True):
            outcome = Verdict.FALSE_NEGATIVE
        case _:
            outcome = Verdict.TRUE_NEGATIVE

    return DocumentVerdict(
        doc_id=score.doc_id,
        tier=score.tier,
        verdict=outcome,
        rules=rules,
        wrong_fields=wrong_fields,
        named_fields=_named_fields(invoice, severity),
        injected=kinds(notes),
    )


def _wrong_fields(score: DocumentScore) -> tuple[str, ...]:
    """The distinct scored fields this document got wrong, in `fields.FIELDS` order.

    Distinct by field name rather than by instance: three misread rows of one column are one wrong
    field here, because the detector's claim is about the document and a count of instances would
    make a long invoice look more broken than a short one that lost the same column.
    """
    seen: list[str] = []
    for result in score.results:
        if result.outcome in DISAGREEMENT and result.field not in seen:
            seen.append(result.field)
    return tuple(seen)


def _fired(invoice: Invoice, severity: Severity) -> tuple[str, ...]:
    seen: list[str] = []
    for violation in invariants.check(invoice):
        if violation.severity is severity and violation.rule not in seen:
            seen.append(violation.rule)
    return tuple(seen)


def _named_fields(invoice: Invoice, severity: Severity) -> tuple[str, ...]:
    named: list[str] = []
    for violation in invariants.check(invoice):
        if violation.severity is not severity:
            continue
        for part in violation.fields:
            named.extend(name for name in covered(part) if name not in named)
    return tuple(named)


def covered(named: str) -> tuple[str, ...]:
    """The scored fields one violation's field name covers.

    `Violation.fields` names the parts of an invoice a rule read — `rate_totals`, `lines`,
    `total_gross`, `seller.nip`. `fields.FIELDS` names what is scored — `rate_totals[].net`,
    `lines[].description`. A rule that read the rate blocks therefore points at both of that block's
    scored fields and at none of the rows', which is the entire content of this mapping.

    A name that covers nothing returns empty rather than raising. `tests/test_eval_detector.py`
    asserts that no rule currently produces one, which is the check that matters: a new rule naming
    a field the scorer does not know about would otherwise silently stop contributing to
    localisation while still counting towards recall.
    """
    return tuple(
        field.name
        for field in fields.FIELDS
        if field.name == named or field.name.startswith(f"{named}[].")
    )


def kinds(notes: Sequence[str]) -> tuple[str, ...]:
    """The corruption kinds a prediction recorded, read off the front of each note.

    `corrupt.Injection.note` is `"<kind> <field>: <before> -> <after>"`, and the kind is the first
    token precisely so it can be read this way. A leading token this package does not recognise is
    dropped rather than guessed: a note something else wrote is not a labelled error, and treating
    it as one would put an invented kind in the per-kind table.
    """
    found = (note.split(" ", 1)[0] for note in notes)
    return tuple(kind for kind in found if kind in corrupt.KINDS)


# --------------------------------------------------------------------------- aggregation


@dataclass(frozen=True, slots=True)
class Counts:
    """A confusion matrix, plus the documents the detector could not be run on at all."""

    true_positive: int = 0
    false_positive: int = 0
    false_negative: int = 0
    true_negative: int = 0
    no_prediction: int = 0

    @property
    def judged(self) -> int:
        """Documents the detector actually ran on. Every rate below has this as its universe."""
        return (
            self.true_positive + self.false_positive + self.false_negative + self.true_negative
        )

    @property
    def documents(self) -> int:
        return self.judged + self.no_prediction

    @property
    def precision(self) -> float | None:
        """Of the documents it flagged, how many were actually wrong — the cost of the gate."""
        return _ratio(self.true_positive, self.true_positive + self.false_positive)

    @property
    def recall(self) -> float | None:
        """Of the documents that were wrong, how many it flagged. The headline number."""
        return _ratio(self.true_positive, self.true_positive + self.false_negative)

    @property
    def specificity(self) -> float | None:
        """Of the documents that were right, how many it left alone."""
        return _ratio(self.true_negative, self.true_negative + self.false_positive)

    @property
    def f1(self) -> float | None:
        """The harmonic mean, and `0.0` — not `None` — when the detector caught nothing.

        An empty denominator has no answer and returns `None` everywhere in this package. A
        detector that fired on nothing that was wrong has an answer, and it is zero: that is a
        measurement of a detector that failed, not a missing measurement.
        """
        precision, recall = self.precision, self.recall
        if precision is None or recall is None:
            return None
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    @property
    def prevalence(self) -> float | None:
        """How many of the judged documents were wrong at all — the floor any recall is read over.

        Without it a recall is uninterpretable: a detector that flags every document scores 1.0,
        and only the prevalence beside it shows that flagging everything was an option.
        """
        return _ratio(self.true_positive + self.false_negative, self.judged)


@dataclass(frozen=True, slots=True)
class RulePerformance:
    """One rule id, and what its firing actually predicted."""

    rule: str
    fired: int
    wrong: int

    @property
    def precision(self) -> float | None:
        """Of the documents this rule fired on, how many were wrong somewhere."""
        return _ratio(self.wrong, self.fired)


@dataclass(frozen=True, slots=True)
class KindRecall:
    """One injected error kind, and whether the arithmetic noticed it.

    Two readings, because a document can carry more than one injected kind and attributing a firing
    to one of them is otherwise a guess:

    * `isolated` restricts to documents where this kind was the only one injected, so a firing is
      attributable to it. **This is the number to read.**
    * `marginal` counts every document carrying the kind, whatever else it carries. Larger support,
      contaminated by co-occurrence — a `date_shifted` that happened to land beside a `vat_cent`
      would otherwise read as a date shift the arithmetic caught.
    """

    kind: str
    #: The severity this row was computed at, so the row can say whether its own zero was expected.
    #: Required rather than defaulted: it decides `out_of_scope`, and a caller who omitted it would
    #: silently get the hard reading of a heuristic table — a wrong label on a metric-bearing row.
    severity: Severity
    isolated_documents: int = 0
    isolated_fired: int = 0
    marginal_documents: int = 0
    marginal_fired: int = 0

    @property
    def isolated_recall(self) -> float | None:
        return _ratio(self.isolated_fired, self.isolated_documents)

    @property
    def marginal_recall(self) -> float | None:
        return _ratio(self.marginal_fired, self.marginal_documents)

    @property
    def expected_invisible(self) -> bool:
        """Whether `corrupt` declares this kind beyond what *any* rule can see."""
        return self.kind in corrupt.INVISIBLE_KINDS

    @property
    def out_of_scope(self) -> bool:
        """Whether some rule is expected to catch this kind, but not one at this severity.

        A transposed total is not a failure of the heuristic half of the rule set and a misread year
        is not a failure of the arithmetic half. Both halves are reported, so both tables contain
        rows the other one owns, and a zero in such a row means "not asked" rather than "missed".
        Without this distinction the heuristic table would read as a detector that catches almost
        nothing — which is what it looked like before there was anything for it to catch.
        """
        expected = corrupt.CAUGHT_BY.get(self.kind)
        return expected is not None and expected is not self.severity


@dataclass(frozen=True, slots=True)
class Study:
    """One severity's worth of detector performance over one run."""

    severity: Severity
    counts: Counts
    verdicts: tuple[DocumentVerdict, ...]
    rules: tuple[RulePerformance, ...]
    kinds: tuple[KindRecall, ...]
    #: True positives whose named fields overlapped a genuinely wrong one.
    localised: int = 0
    #: True positives at all — the denominator of `localisation`.
    localisable: int = 0

    @property
    def localisation(self) -> float | None:
        """Of the documents it correctly flagged, how many it also pointed at the right field.

        Reported apart from precision and recall because it is a strictly weaker claim than either,
        and a detector can be useful for routing while being poor at this. Folding it in would let
        a rule that names half the invoice look like it had explained something.
        """
        return _ratio(self.localised, self.localisable)


def summarise(
    verdicts: Iterable[DocumentVerdict], *, severity: Severity = Severity.HARD
) -> Study:
    """Verdicts into counts. Pure, and it never re-reads an invoice.

    Takes verdicts rather than documents so the expensive half — running every rule over every
    prediction — happens exactly once, and so a caller can filter a population (one tier, one
    template, one corruption kind) and re-summarise without recomputing anything.
    """
    rows = tuple(verdicts)
    return Study(
        severity=severity,
        counts=_counts(rows),
        verdicts=rows,
        rules=_rules(rows),
        kinds=_kinds(rows, severity),
        localised=sum(1 for row in rows if row.localised),
        localisable=sum(1 for row in rows if row.verdict is Verdict.TRUE_POSITIVE),
    )


def _counts(rows: Sequence[DocumentVerdict]) -> Counts:
    tally = {outcome: 0 for outcome in Verdict}
    for row in rows:
        tally[row.verdict] += 1
    return Counts(
        true_positive=tally[Verdict.TRUE_POSITIVE],
        false_positive=tally[Verdict.FALSE_POSITIVE],
        false_negative=tally[Verdict.FALSE_NEGATIVE],
        true_negative=tally[Verdict.TRUE_NEGATIVE],
        no_prediction=tally[Verdict.NO_PREDICTION],
    )


def _rules(rows: Sequence[DocumentVerdict]) -> tuple[RulePerformance, ...]:
    """Per-rule precision, over the documents each rule fired on.

    Ordered by how often a rule fired, then by name, so the table opens on the rule doing the work
    rather than on whichever id sorts first. A rule that never fired is left out entirely: a row of
    zeroes and a dash says nothing that its absence does not, and the rule set is listed in
    `invariants` for anyone who wants the full inventory.
    """
    fired: dict[str, int] = {}
    wrong: dict[str, int] = {}
    for row in rows:
        for rule in row.rules:
            fired[rule] = fired.get(rule, 0) + 1
            wrong[rule] = wrong.get(rule, 0) + int(row.wrong)
    return tuple(
        sorted(
            (RulePerformance(rule=rule, fired=count, wrong=wrong[rule])
             for rule, count in fired.items()),
            key=lambda row: (-row.fired, row.rule),
        )
    )


def _kinds(rows: Sequence[DocumentVerdict], severity: Severity) -> tuple[KindRecall, ...]:
    """Per-kind recall, in `corrupt.KINDS` order so the table is stable across runs.

    Kinds that were never injected are dropped: on a run that injects nothing — every baseline but
    the noisy oracle — this returns empty rather than eleven rows of dashes.
    """
    isolated_documents: dict[str, int] = {}
    isolated_fired: dict[str, int] = {}
    marginal_documents: dict[str, int] = {}
    marginal_fired: dict[str, int] = {}

    for row in rows:
        if row.verdict is Verdict.NO_PREDICTION:
            #: The detector never ran on this document, so it is neither a catch nor a miss — the
            #: same exclusion `Counts` makes. Counting it here would deflate the very number the
            #: blind-spot table exists to show, by charging the rules with a refusal upstream.
            continue
        present = set(row.injected)
        for kind in present:
            marginal_documents[kind] = marginal_documents.get(kind, 0) + 1
            marginal_fired[kind] = marginal_fired.get(kind, 0) + int(row.fired)
        if len(present) == 1:
            kind = next(iter(present))
            isolated_documents[kind] = isolated_documents.get(kind, 0) + 1
            isolated_fired[kind] = isolated_fired.get(kind, 0) + int(row.fired)

    return tuple(
        KindRecall(
            kind=kind,
            severity=severity,
            isolated_documents=isolated_documents.get(kind, 0),
            isolated_fired=isolated_fired.get(kind, 0),
            marginal_documents=marginal_documents.get(kind, 0),
            marginal_fired=marginal_fired.get(kind, 0),
        )
        for kind in corrupt.KINDS
        if kind in marginal_documents
    )


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator
