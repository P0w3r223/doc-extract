"""A `Curve` as Markdown. Formatting only — nothing below computes a number.

Two qualifications this report has to carry, both of which are easy to leave out and both of which
change how the numbers should be read:

* **Coverage is over values the model asserted.** A gate that only sees what was answered cannot
  see what was dropped, so `missed` is printed above the curve rather than after it.
* **A rate with no denominator prints as `—`.** On a run where nothing was wrong, the gate has no
  leakage to report and a `0 %` would read as a measurement of a gate that was never tested.
"""

from __future__ import annotations

from collections.abc import Iterable

from doc_extract.decide.confidence import ROUTES
from doc_extract.eval.format import rate as _rate
from doc_extract.eval.predictions import RunMeta
from doc_extract.eval.selective import Curve


def render(curve: Curve, *, run: RunMeta, directory: str = "") -> str:
    parts = [
        _header(curve, run=run, directory=directory),
        _signals(curve),
        _curve(curve),
        _caveats(curve),
    ]
    return "\n\n".join(part for part in parts if part) + "\n"


def _header(curve: Curve, *, run: RunMeta, directory: str) -> str:
    lines = [
        f"# the gate — {run.model}",
        "",
        "| | |",
        "|---|---|",
        f"| answered by | `{run.model}` |",
        f"| saw | {run.options.get('sees', 'unstated')} |",
        f"| values asserted | {curve.asserted} |",
        f"| of which wrong | {curve.wrong} |",
        f"| gold values never asserted | {curve.missed} |",
        f"| asserted but not assessable | {curve.unassessable} |",
        f"| documents with no invoice | {curve.without_prediction} |",
    ]
    if directory:
        lines.insert(4, f"| run | `{directory}` |")
    return "\n".join(lines)


def _signals(curve: Curve) -> str:
    """Each signal alone, before the gate combines them."""
    return "\n".join([
        "## The two signals, scored apart",
        "",
        "Field-level detectors of a wrong asserted value. They are complements with very different "
        "shapes, and a reader who saw only their combination could not tell which did the work.",
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


def _caveats(curve: Curve) -> str:
    lines = ["## Read this before the tables", ""]

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
            "non-numeric rate is an exemption code each issuer abbreviates their own way. They are "
            "values a model can get wrong, and nothing above measures whether it did."
        )
    if curve.without_prediction:
        lines.append(
            f"* {curve.without_prediction} document(s) produced no invoice, so none of their "
            "fields was assessed. The pipeline had already refused them."
        )
    if curve.without_text:
        share = curve.without_text / curve.asserted if curve.asserted else None
        lines.append(
            f"* **{curve.without_text} of the {curve.asserted} assessed value(s) "
            f"({_rate(share)}) sit on a page with no text layer at all.** Grounding resolves a "
            "value against page text and there is none, so it returns `UNGROUNDED` for every one "
            "of them — correct or not. Nothing here distinguishes *this value is not on the page* "
            "from *there was no page to look in*, which means the coverage figure above is partly "
            "a measurement of the missing text layer rather than of the reader. Read the accuracy "
            "at `none` — accepting everything — as the comparison that is not affected by it."
        )
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
    if "grounding" in silent:
        lines.append(
            f"* **`grounding` flagged nothing at all**, while {curve.wrong} asserted value(s) were "
            "wrong. It asks whether a value is *on the page*, not whether it is in the *right "
            "place*: a reader that lifts a real figure out of the wrong column is fully grounded "
            "and completely wrong, and one that borrows a word from the other party's address is "
            "too. The spans are recorded, so a geometric check could ask the second question — it "
            "is not built."
        )
    if "arithmetic" in silent:
        lines.append(
            f"* **`arithmetic` flagged nothing at all**, while {curve.wrong} asserted value(s) "
            "were wrong. No identity was broken: a prediction can be internally consistent and "
            "still be wrong everywhere, which is what a constant or a wholly-invented answer looks "
            "like from the arithmetic's side."
        )
    lines.append(
        "* The confidence levels are produced by fixed rules over the two signals, not by weights "
        "fitted to this corpus. That is why there are four of them and not a smooth sweep: a "
        "fitted score would draw a better curve here and would be measuring its own training set."
    )
    return "\n".join(lines)


def summary_lines(curve: Curve) -> Iterable[str]:
    """What a terminal wants after a run, without the tables."""
    yield f"asserted   : {curve.asserted}   wrong: {curve.wrong}   never asserted: {curve.missed}"
    for signal in curve.signals:
        yield (
            f"  {signal.name:<11} precision {_rate(signal.precision)}   "
            f"recall {_rate(signal.recall)}"
        )
    for point in curve.points:
        yield (
            f"  accept>={point.level.name.lower():<7} coverage {_rate(point.coverage)}   "
            f"accuracy {_rate(point.accuracy)}   leaked {point.leaked}"
        )
