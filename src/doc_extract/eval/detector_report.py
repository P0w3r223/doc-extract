"""A `Study` as Markdown. Formatting only — no number below is computed here.

The same separation `report` keeps, for the same reason, and with two qualifications this study
needs and the scoring report does not:

* **A rate over an empty denominator prints as `—`.** A detector run against a population with no
  errors in it has no recall, and printing `0 %` would say it missed something. `claude` on this
  corpus is exactly that case, so the dash is load-bearing rather than defensive.
* **Prevalence is printed above precision and recall, not below them.** A recall is uninterpretable
  without it: a detector that flags every document scores 1.0, and only the prevalence beside it
  shows that flagging everything was available.
"""

from __future__ import annotations

from collections.abc import Iterable

from doc_extract.eval.detector import KindRecall, Study
from doc_extract.eval.format import rate as _rate
from doc_extract.eval.predictions import RunMeta


def render(study: Study, *, run: RunMeta, directory: str = "") -> str:
    """The whole detector report for one run at one severity."""
    parts = [
        _header(study, run=run, directory=directory),
        _matrix(study),
        _rules(study),
        _kinds(study),
        _caveats(study, run=run),
    ]
    return "\n\n".join(part for part in parts if part) + "\n"


def _header(study: Study, *, run: RunMeta, directory: str) -> str:
    counts = study.counts
    lines = [
        f"# detector — {run.model}, {study.severity} rules",
        "",
        "| | |",
        "|---|---|",
        f"| answered by | `{run.model}` |",
        f"| baseline | `{run.baseline}` |",
        f"| saw | {run.options.get('sees', 'unstated')} |",
        f"| severity | `{study.severity}` |",
        f"| documents | {counts.documents} |",
        f"| judged | {counts.judged} |",
        f"| no prediction | {counts.no_prediction} |",
    ]
    if directory:
        lines.insert(4, f"| run | `{directory}` |")
    return "\n".join(lines)


def _matrix(study: Study) -> str:
    """The question, the confusion matrix, and the rates that follow from it."""
    counts = study.counts
    return "\n".join([
        '## Does "the arithmetic holds" predict "the fields are right"?',
        "",
        "The detector is `invariants.check` run on the **prediction**, never on the gold: the "
        "signal has to be available at inference time on a document nobody annotated.",
        "",
        "| | flagged | silent |",
        "|---|---:|---:|",
        f"| **fields wrong** | {counts.true_positive} | {counts.false_negative} |",
        f"| **fields right** | {counts.false_positive} | {counts.true_negative} |",
        "",
        "| | |",
        "|---|---:|",
        f"| prevalence | {_rate(counts.prevalence)} |",
        f"| precision | {_rate(counts.precision)} |",
        f"| recall | {_rate(counts.recall)} |",
        f"| F1 | {_rate(counts.f1)} |",
        f"| specificity | {_rate(counts.specificity)} |",
        f"| localisation | {_rate(study.localisation)} "
        f"({study.localised} / {study.localisable}) |",
    ])


def _rules(study: Study) -> str:
    if not study.rules:
        return ""
    return "\n".join([
        "## Per rule",
        "",
        "Precision only. A rule's recall is not a quantity this study can report: a document is "
        "wrong or not, and which rule *should* have caught it is not something the gold says.",
        "",
        "| rule | fired on | of which wrong | precision |",
        "|---|---:|---:|---:|",
        *(
            f"| `{row.rule}` | {row.fired} | {row.wrong} | {_rate(row.precision)} |"
            for row in study.rules
        ),
    ])


def _kinds(study: Study) -> str:
    if not study.kinds:
        return ""
    return "\n".join([
        "## Per injected error kind",
        "",
        "`isolated` counts only the documents where this was the **only** kind injected, so a "
        "firing is attributable to it. `marginal` counts every document carrying the kind and is "
        "contaminated by whatever else landed beside it. Read the isolated column.",
        "",
        "The last column says whether a zero was expected. **`not asked` is not a miss**: this is "
        f"the `{study.severity}` half of the rule set, and a kind the *other* half owns was never "
        "put to it. `declared invisible` is the finding — no rule at either severity can see it.",
        "",
        "| kind | isolated | n | marginal | n | |",
        "|---|---:|---:|---:|---:|---|",
        *(
            f"| `{row.kind}` | {_rate(row.isolated_recall)} | {row.isolated_documents} | "
            f"{_rate(row.marginal_recall)} | {row.marginal_documents} | {_scope(row)} |"
            for row in study.kinds
        ),
    ])


def _scope(row: KindRecall) -> str:
    if row.expected_invisible:
        return "declared invisible"
    return "not asked" if row.out_of_scope else ""


def _caveats(study: Study, *, run: RunMeta) -> str:
    counts = study.counts
    lines = ["## Read this before the tables", ""]
    #: First, because it reframes what "wrong" means in every sentence under it — including the
    #: one that would otherwise call a run with no misreadings a detector that caught nothing.
    if run.attacked:
        lines.append(run.ATTACKED_CAVEAT)

    if counts.prevalence == 0:
        lines.append(
            "* **Nothing was wrong on any judged document, so there was nothing to detect.** "
            "Precision and recall have no denominator and print as a dash. The one number this "
            f"run does establish is the false-positive rate: {counts.false_positive} of "
            f"{counts.judged} correctly-read documents were flagged — a gate that does not block "
            "correct work. It says nothing about whether the gate catches incorrect work."
        )
    elif counts.judged and counts.prevalence == 1:
        lines.append(
            f"* **Every one of the {counts.judged} judged documents was wrong, so a false positive "
            "was impossible.** Precision"
            + (f" prints {_rate(counts.precision)}, and it" if counts.precision is not None else "")
            + " has no adversary here and cannot be read as one: a rule that fired on *every* "
            "document would print the same figure. Specificity, whose denominator is the correct "
            "documents, prints a dash for the same reason. **The rate this arm establishes is the "
            "recall.** It is the mirror of a run with nothing wrong in it, where the recall is the "
            "undefined one — and it is the more flattering of the two, which is why it is printed "
            "rather than left to be noticed."
        )

    if counts.recall == 0 and counts.prevalence:
        lines.append(
            "* **The detector caught nothing.** Every wrong document passed. A prediction can be "
            "internally consistent and still be wrong everywhere, and arithmetic cannot see the "
            "difference."
        )

    if counts.no_prediction:
        lines.append(
            f"* {counts.no_prediction} document(s) produced no invoice, so no rule could read one. "
            "They are outside every denominator above. The pipeline had already refused them on "
            "its own; counting them as catches would credit the invariants with that refusal."
        )

    lines.append(
        f"* This is the **{study.severity}** half of the rule set, reported alone. Hard rules are "
        "arithmetic identities and a violation means something is genuinely wrong; heuristics have "
        "lawful exceptions. Pooling them would let a rule with known false positives borrow the "
        "precision of rules that have none."
    )
    lines.append(
        "* Localisation is reported apart from precision because it is a strictly weaker claim: a "
        "rule can be right that a document is broken and wrong about which field broke it."
    )
    return "\n".join(lines)


def summary_lines(study: Study) -> Iterable[str]:
    """What a terminal wants after a study, without the tables."""
    counts = study.counts
    yield (
        f"{study.severity:<10} judged {counts.judged}"
        + (f" (+{counts.no_prediction} without a prediction)" if counts.no_prediction else "")
    )
    yield (
        f"           TP {counts.true_positive}  FP {counts.false_positive}  "
        f"FN {counts.false_negative}  TN {counts.true_negative}"
    )
    yield (
        f"           prevalence {_rate(counts.prevalence)}   "
        f"precision {_rate(counts.precision)}   recall {_rate(counts.recall)}"
    )
