"""A `Curve` as Markdown. Formatting only — nothing below computes a number.

Two qualifications this report has to carry, both of which are easy to leave out and both of which
change how the numbers should be read:

* **Coverage is over values the model asserted.** A gate that only sees what was answered cannot
  see what was dropped, so `missed` is printed above the curve rather than after it.
* **And over values it could be asked about.** On a page with no text layer grounding has nothing
  to search, so those values leave the curve rather than filling it with `UNGROUNDED`. The count is
  printed above the tables, because a curve over a third of a corpus should say which third.
* **A rate with no denominator prints as `—`.** On a run where nothing was wrong, the gate has no
  leakage to report and a `0 %` would read as a measurement of a gate that was never tested.
"""

from __future__ import annotations

from collections.abc import Iterable

from doc_extract.decide.confidence import ROUTES
from doc_extract.eval.format import rate as _rate
from doc_extract.eval.predictions import RunMeta
from doc_extract.eval.selective import LEVELS, Curve


def render(curve: Curve, *, run: RunMeta, directory: str = "") -> str:
    parts = [
        _header(curve, run=run, directory=directory),
        _signals(curve),
        _curve(curve),
        _caveats(curve, run=run),
    ]
    return "\n\n".join(part for part in parts if part) + "\n"


def _header(curve: Curve, *, run: RunMeta, directory: str) -> str:
    declined = _with_wrong(curve.unassessable, curve.wrong_unassessable)
    textless = _with_wrong(curve.without_text, curve.wrong_without_text)
    lines = [
        f"# the gate — {run.model}",
        "",
        "| | |",
        "|---|---|",
        f"| answered by | `{run.model}` |",
        f"| saw | {run.options.get('sees', 'unstated')} |",
        f"| values asserted | {curve.offered} |",
        f"| of which wrong | {curve.wrong_everywhere} |",
        f"| assessed below | {curve.assessed} |",
        f"| of those, wrong | {curve.wrong} |",
        f"| asserted but not assessable | {declined} |",
        f"| asserted on a page with no text | {textless} |",
        f"| gold values never asserted | {curve.missed} |",
        f"| documents with no invoice | {curve.without_prediction} |",
    ]
    if directory:
        lines.insert(4, f"| run | `{directory}` |")
    return "\n".join(lines)


def _ungated(curve: Curve) -> str:
    """The comparison the curve stops being able to make, and the verdict it implies.

    The `none` row means *accept everything this gate could assess*. Where most of a corpus left
    the curve that is no longer the policy a reader is choosing against — not gating at all means
    accepting the excluded values too. So the honest baseline is computed over everything the model
    asserted, and the verdict is read off the comparison rather than written into it: the sentence
    that said the gate had stopped helping outlived the change that fixed it, once already.
    """
    top = next((point for point in curve.points if point.level is LEVELS[0]), None)
    ungated = curve.ungated_accuracy
    if top is None or top.accuracy is None or ungated is None:  # pragma: no cover — empty curve
        return "* No accepted values, so there is no gated policy to compare against."
    verdict = (
        "**still less accurate than not gating at all**, because its signal exists only where the "
        "page kept text and the excluded values are largely right"
        if top.accuracy < ungated else
        "**more accurate than not gating at all**, which is what a gate is for"
    )
    return (
        f"* **Against the ungated policy.** Accepting every asserted value — the {curve.assessed} "
        f"below plus the {curve.offered - curve.assessed} excluded from them — is "
        f"{_rate(ungated)} accurate. The `high` row is {_rate(top.accuracy)}, so on this corpus "
        f"auto-accepting the gate's confident bucket is {verdict}. The `none` row is *not* that "
        "comparison: it accepts everything the gate could assess, which is a different set."
    )


def _with_wrong(total: int, wrong: int) -> str:
    """A count, and what is inside it. The size of a blind spot is not its contents."""
    return f"{total} (wrong: {wrong})" if total else str(total)


def _signals(curve: Curve) -> str:
    """Each signal alone, before the gate combines them."""
    return "\n".join([
        "## The four signals, scored apart",
        "",
        "Field-level detectors of a wrong asserted value. They are complements with very different "
        "shapes, and a reader who saw only their combination could not tell which did the work. "
        "`contention` is the one that accuses a **pair**: when two of a reading's values claim one "
        "printed figure it flags both, because no label-free fact says which of the two is the "
        "intruder. Where the sibling is a correct reading that caps its precision near a half; "
        "where both belong to a row the page never printed, nothing it flags is correct and the "
        "row below says which of the two this run is. `completeness` asks the opposite of "
        "grounding: not whether the value is on the page but whether the page kept printing it "
        "after the reading stopped.",
        "",
        "| signal | TP | FP | FN | TN | precision | recall |",
        "|---|---:|---:|---:|---:|---:|---:|",
        *(
            f"| `{signal.name}` | {signal.true_positive} | {signal.false_positive} | "
            f"{signal.false_negative} | {signal.true_negative} | "
            f"{_rate(signal.precision)} | {_rate(signal.recall)} |"
            for signal in curve.signals
        ),
    ])


def _curve(curve: Curve) -> str:
    """The coverage-accuracy curve, cumulative from the most confident level down."""
    return "\n".join([
        "## Coverage and accuracy",
        "",
        "Cumulative: each row accepts everything at its level **and above**. `leaked` counts "
        "the wrong values accepted, which is what a gate is actually judged on.",
        "",
        "| accept down to | route | coverage | accuracy | accepted | leaked |",
        "|---|---|---:|---:|---:|---:|",
        *(
            f"| `{point.level.name.lower()}` | `{ROUTES[point.level]}` | "
            f"{_rate(point.coverage)} | {_rate(point.accuracy)} | "
            f"{point.accepted} | {point.leaked} |"
            for point in curve.points
        ),
    ])


def _caveats(curve: Curve, *, run: RunMeta) -> str:
    lines = ["## Read this before the tables", ""]
    if run.attacked:
        lines.append(run.ATTACKED_CAVEAT)

    lines.append(
        "* **Coverage is over the values the model asserted, not over the document.** A field it "
        f"left `null` cannot be grounded, so it carries no confidence and sits outside every "
        f"denominator above. {curve.missed} gold value(s) were never asserted at all, and no "
        "signal here can see them — a model that answered less would score better on this curve."
    )
    if curve.unassessable:
        lines.append(
            f"* {curve.unassessable} asserted value(s) are **outside the curve** because grounding "
            "declines to ask about them: `kind` is an FA(3) code the page never prints, and a "
            "non-numeric rate is an exemption code each issuer abbreviates their own way. "
            f"{curve.wrong_unassessable} of them are wrong, and nothing in the tables above "
            "counts those."
        )
    if curve.without_prediction:
        lines.append(
            f"* {curve.without_prediction} document(s) produced no invoice, so none of their "
            "fields was assessed. The pipeline had already refused them."
        )
    if curve.without_text:
        share = curve.without_text / curve.offered if curve.offered else None
        lines.append(
            f"* **{curve.without_text} of the {curve.offered} asserted value(s) ({_rate(share)}) "
            "sit on a page with no text layer at all, and are outside the curve.** Grounding "
            "resolves a value against page text and there is none, so it answers `NO_TEXT` — *I "
            "could not ask* — rather than `UNGROUNDED`, which would have claimed the value is "
            "missing from the page. They are routed `review` and carry no confidence, so every "
            f"figure above is over the {curve.assessed} value(s) this pipeline could actually "
            f"assess, and {curve.wrong_without_text} wrong value(s) sit in the excluded set where "
            "nothing measures them. **The gate has no signal at all on those**, and that is a "
            "statement about the page rather than about the reader: a recogniser in front of the "
            "model brings the signal back."
        )
        lines.append(_ungated(curve))
    if curve.wrong == 0:
        lines.append(
            "* **Nothing asserted was wrong**, so the gate had nothing to catch. Accuracy is 100 % "
            "at every level and the curve is flat by construction; it says the gate does not block "
            "correct work, and nothing about whether it blocks incorrect work."
        )

    silent = {
        signal.name for signal in curve.signals
        if curve.wrong and signal.true_positive == 0 and signal.false_positive == 0
    }
    lines.extend(_grounding_misses(curve))
    lines.extend(_contention_added(curve))
    lines.extend(_completeness_added(curve))
    if "arithmetic" in silent:
        lines.append(
            f"* **`arithmetic` flagged nothing at all**, while {curve.wrong} asserted value(s) "
            "were wrong. No identity was broken: a prediction can be internally consistent and "
            "still be wrong everywhere, which is what a constant or a wholly-invented answer looks "
            "like from the arithmetic's side."
        )
    lines.append(
        "* The confidence levels are produced by fixed rules over the four signals, not by "
        "weights fitted to this corpus. That is why there are four and not a smooth sweep: a "
        "fitted score would draw a better curve here and would be measuring its own training set."
    )
    return "\n".join(lines)


def _contention_added(curve: Curve) -> list[str]:
    """What the third signal contributed **beyond** the arithmetic, from this run's own counts.

    The two overlap by construction: a row whose discount duplicates its net breaks
    `lines.net_matches_quantity_times_price` as well, so the arithmetic has usually already named
    the field by the time a contention does. Whether that leaves the newer signal doing anything is
    a question about a particular run, and the answer is derived here rather than settled in prose —
    the same reason `ungated_accuracy` is computed: a sentence in a docstring survives the day the
    counts stop supporting it.
    """
    flagged = [row for row in curve.judged if row.contended]
    if not flagged:
        return []
    alone = [row for row in flagged if not row.accused]
    wrong_alone = sum(1 for row in alone if row.wrong)
    verdict = (
        f"{len(alone)} of them ({wrong_alone} wrong) carried **no** arithmetic accusation, so the "
        "gate would not have demoted them otherwise"
        if alone else
        "**every one of them was already named by a hard rule**, so the gate reached the same "
        "verdict without it and what this signal adds here is the attribution, not the routing"
    )
    return [
        f"* `contention` flagged {len(flagged)} asserted value(s), and {verdict}. It names the two "
        "fields that share a printed figure, where an arithmetic violation names the whole `lines` "
        "collection; the two catch overlapping populations and only the narrower one says *which* "
        "values are involved."
    ]


def _completeness_added(curve: Curve) -> list[str]:
    """What the fourth signal contributed **beyond** the other three, from this run's own counts.

    Derived rather than settled in prose for the same reason `_contention_added` is: the signal
    exists because grounding is blind to a description that stops early, and whether that blindness
    was the *only* thing standing between the gate and those values is a question about a
    particular run. On a run where the arithmetic happened to accuse the same rows, the answer is
    that it added attribution and not routing, and a sentence in a docstring would go on claiming
    otherwise.
    """
    flagged = [row for row in curve.judged if row.cut_short]
    if not flagged:
        return []
    alone = [row for row in flagged if not row.ungrounded and not row.accused and not row.contended]
    wrong_alone = sum(1 for row in alone if row.wrong)
    verdict = (
        f"{len(alone)} of them ({wrong_alone} wrong) carried **no** other signal, so the gate "
        "would have accepted them"
        if alone else
        "**every one of them was already flagged by another signal**, so the gate reached the same "
        "verdict without it"
    )
    return [
        f"* `completeness` flagged {len(flagged)} asserted value(s), and {verdict}. It is the one "
        "signal aimed at grounding's standing blind spot: a value that stops early is a real "
        "string, in the right place, and only the page's own wrapping says it is not the whole one."
    ]


def _grounding_misses(curve: Curve) -> list[str]:
    """The standing limit of grounding, printed when this run's own counts show it biting.

    Grounding asks whether a value is on the page, never whether it is in the *place* that field is
    printed. A reader that lifts a real figure out of the wrong column is fully grounded and
    completely wrong. The bullet appears when grounding **missed more wrong values than it caught**
    — a comparison between two counts of this run, so nothing here is a threshold picked to make a
    report say something.

    The wording splits on whether it caught anything at all, because *flagged nothing* and *flagged
    a few* are different claims and a reader deciding how much to trust the signal needs the one
    that is true. The earlier version printed only the first, which meant the limit went unstated
    on exactly the runs where the signal was weak rather than absent.
    """
    grounding = next((s for s in curve.signals if s.name == "grounding"), None)
    if grounding is None or not curve.wrong or grounding.false_negative <= grounding.true_positive:
        return []
    caught = (
        "**flagged nothing at all**" if grounding.true_positive == 0
        else f"flagged {grounding.true_positive} of them"
    )
    return [
        f"* **`grounding` missed {grounding.false_negative} of the {curve.wrong} wrong asserted "
        f"value(s)** and {caught}. It asks whether a value is *on the page*, not whether it is in "
        "the *right place*: a reader that lifts a real figure out of the wrong column is fully "
        "grounded and completely wrong, and one that borrows a word from the other party's address "
        "is too. A **text** value is now resolved to one place rather than to whichever occurrence "
        "of each word came first, which is what makes its recorded spans a location at all; an "
        "amount or an identifier still resolves to every occurrence of itself. `contention` uses "
        "those places to catch the one wrong-column shape that is decidable without knowing which "
        "column is which — two values claiming one figure — and `docs/adr/0002_placement.md` "
        "carries the two shapes that leaves standing."
    ]


def summary_lines(curve: Curve) -> Iterable[str]:
    """What a terminal wants after a run, without the tables."""
    yield (
        f"asserted   : {curve.offered}   wrong: {curve.wrong_everywhere}   "
        f"assessed: {curve.assessed}   never asserted: {curve.missed}"
    )
    for signal in curve.signals:
        yield (
            f"  {signal.name:<16} precision {_rate(signal.precision)}   "
            f"recall {_rate(signal.recall)}"
        )
    for point in curve.points:
        yield (
            f"  accept>={point.level.name.lower():<7} coverage {_rate(point.coverage)}   "
            f"accuracy {_rate(point.accuracy)}   leaked {point.leaked}"
        )
