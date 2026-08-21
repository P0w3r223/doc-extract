"""A `Report` as Markdown: the tables, with the qualifications printed beside the numbers.

Rendering is separated from counting so that no number is computed here. Everything below is
formatting — which is also why the awkward parts of the metric rules are enforceable at this layer:

* **An undefined rate prints as `—`, never as `0 %`.** `aggregate` returns `None` for an empty
  denominator; a renderer that coerced it would put a measurement in the table that nobody made.
* **Support is on every row, next to the rate it qualifies.** A 100 % on a support of two is a
  number a reader should be able to discount without leaving the table.
* **What the baseline was allowed to see is in the header.** `oracle` scores near-perfectly because
  it was handed the gold; a table of its numbers with that fact on another page would be
  misleading, and this is the page.
* **Partial coverage is a banner, not a footnote.** A report over a subset says so above its first
  table.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from doc_extract.eval.aggregate import Report, Tally
from doc_extract.eval.corrupt import KINDS
from doc_extract.eval.format import DASH as _DASH
from doc_extract.eval.format import rate as _rate
from doc_extract.eval.predictions import Prediction


def render(report: Report, *, predictions: Sequence[Prediction] = ()) -> str:
    """The whole report. `predictions` is optional and adds the sections that need the raw rows."""
    parts = [
        _header(report),
        _summary(report),
        _table("Per field", report.by_field, key="field"),
        _table("Per group", report.by_group, key="group"),
        _table("Per tier", report.by_tier, key="tier"),
        _table("Per template", report.by_template, key="template"),
        _failures(report),
        _cost(report),
    ]
    injected = _injected(predictions)
    if injected:
        parts.append(injected)
    parts.append(_caveats(report))
    return "\n\n".join(part for part in parts if part) + "\n"


def _header(report: Report) -> str:
    run = report.run
    corpus = run.corpus
    lines = [
        f"# {run.baseline} — {report.documents} documents",
        "",
        "| | |",
        "|---|---|",
        f"| baseline | `{run.baseline}` |",
        f"| answered by | `{run.model}` |",
        f"| saw | {run.options.get('sees', 'unstated')} |",
        f"| corpus | `{run.corpus_dir}` |",
        f"| corpus seed | {corpus.get('corpus_seed', _DASH)} |",
        f"| corpus built with | doc-extract {corpus.get('doc_extract_version', _DASH)}, "
        f"reportlab {corpus.get('reportlab_version', _DASH)} |",
        f"| budgets | extract {run.max_tokens}, repair {run.repair_max_tokens}, "
        f"at most {run.max_repairs} repair(s) |",
        f"| started | {run.started_at} |",
    ]
    if run.effort:
        lines.append(f"| effort | {run.effort} |")
    for name, value in sorted(run.options.items()):
        if name != "sees":
            lines.append(f"| {name} | {value} |")
    return "\n".join(lines)


def _summary(report: Report) -> str:
    overall = report.overall
    coverage = report.coverage
    banner = (
        ""
        if coverage.complete
        else (
            f"> **Partial coverage.** {len(coverage.scored)} of {len(coverage.expected)} documents "
            f"scored; {len(coverage.missing)} missing, {len(coverage.unexpected)} not in the "
            "manifest. Every rate below is over the subset.\n\n"
        )
    )
    return banner + "\n".join([
        "## Summary",
        "",
        "| | |",
        "|---|---|",
        f"| documents scored | {report.documents} of {len(coverage.expected)} "
        f"({_rate(coverage.ratio)}) |",
        f"| produced an invoice | {report.extracted} "
        f"({_rate(_ratio(report.extracted, report.documents))}) |",
        f"| every field right | {report.exact} "
        f"({_rate(_ratio(report.exact, report.documents))}) |",
        f"| field instances | {overall.instances} "
        f"(support {overall.support}, correctly absent {overall.absent}) |",
        f"| detection recall | {_rate(overall.detection_recall)} |",
        f"| detection precision | {_rate(overall.detection_precision)} |",
        f"| value accuracy | {_rate(overall.value_accuracy)} |",
        f"| accuracy | {_rate(overall.accuracy)} |",
    ])


def _table(title: str, rows: Sequence[tuple[str, Tally]], *, key: str) -> str:
    if not rows:
        return ""
    header = [
        f"## {title}",
        "",
        f"| {key} | support | correct | wrong | missed | spurious | recall | precision | "
        "value acc. | accuracy |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    body = [
        f"| `{name}` | {counts.support} | {counts.correct} | {counts.wrong} | {counts.missed} | "
        f"{counts.spurious} | {_rate(counts.detection_recall)} | "
        f"{_rate(counts.detection_precision)} | {_rate(counts.value_accuracy)} | "
        f"{_rate(counts.accuracy)} |"
        for name, counts in rows
    ]
    return "\n".join(header + body)


def _failures(report: Report) -> str:
    return "\n".join([
        "## Failures and stop reasons",
        "",
        "| failure class | documents |",
        "|---|---:|",
        *(f"| `{name}` | {count} |" for name, count in report.failures),
        "",
        "| stop reason | documents |",
        "|---|---:|",
        *(f"| `{name or '(none)'}` | {count} |" for name, count in report.stop_reasons),
    ])


def _cost(report: Report) -> str:
    usage = report.usage
    return "\n".join([
        "## Cost",
        "",
        "Over **every** attempt, including the ones that failed and were repaired.",
        "",
        "| | |",
        "|---|---:|",
        f"| attempts | {report.attempts} |",
        f"| of which repairs | {report.repairs} |",
        f"| input tokens | {usage.input_tokens} |",
        f"| output tokens | {usage.output_tokens} |",
        f"| cache write tokens | {usage.cache_creation_input_tokens} |",
        f"| cache read tokens | {usage.cache_read_input_tokens} |",
    ])


def _injected(predictions: Sequence[Prediction]) -> str:
    """What the noisy oracle broke, by kind. Empty for every baseline that only reads.

    A note whose first token is not a known kind is not an injected error. `stripped` records what
    it removed the same way, and counting those as errors printed *"108 of 108 documents carry at
    least one known error"* above a table with no rows in it. `detector.kinds` already takes this
    position — an unrecognised token is dropped rather than guessed at — and the two modules read
    the same notes, so they cannot be allowed to disagree about what one means.
    """
    counts = {kind: 0 for kind in KINDS}
    documents = 0
    for prediction in predictions:
        kinds = {note.split(" ", 1)[0] for note in prediction.notes} & set(KINDS)
        documents += bool(kinds)
        for kind in kinds:
            counts[kind] += 1
    if not documents:
        return ""
    return "\n".join([
        "## Injected errors",
        "",
        f"{documents} of {len(predictions)} documents carry at least one known error.",
        "",
        "| kind | documents |",
        "|---|---:|",
        *(f"| `{kind}` | {count} |" for kind, count in counts.items() if count),
    ])


def _caveats(report: Report) -> str:
    lines = ["## Read this before the tables", ""]
    if report.run.attacked:
        lines.append(report.run.ATTACKED_CAVEAT)
    unsupported = report.unsupported_fields
    if unsupported:
        lines.append(
            "* Fields the corpus never carries, so they have no support and no accuracy: "
            + ", ".join(f"`{name}`" for name in unsupported)
            + ". A dash in their row is an absence of evidence, not a score of zero."
        )
    sees = str(report.run.options.get("sees", "unstated"))
    lines.append(
        f"* This baseline saw **{sees}**."
        + (
            " A number produced by something that was handed the answer is a check on the harness,"
            " not a result about extraction."
            if sees == "the gold"
            else ""
        )
    )
    lines.append(
        "* Detection and value accuracy are separate columns on purpose. A field that is half "
        "missed and a field that is half misread both read as 50 % accuracy and need different "
        "work."
    )
    if not report.coverage.complete:
        lines.append(
            "* **Coverage is incomplete**, so no number here is a result about the corpus as a "
            "whole."
        )
    return "\n".join(lines)


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def summary_lines(report: Report) -> Iterable[str]:
    """The three numbers a terminal wants after a run, without the tables."""
    yield f"documents  : {report.documents} of {len(report.coverage.expected)}"
    yield f"extracted  : {report.extracted}   exact: {report.exact}"
    yield (
        f"accuracy   : {_rate(report.overall.accuracy)}   "
        f"(recall {_rate(report.overall.detection_recall)}, "
        f"value {_rate(report.overall.value_accuracy)}, support {report.overall.support})"
    )
