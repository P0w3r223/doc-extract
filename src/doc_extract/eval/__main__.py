"""Run a baseline over the corpus, score predictions already written, or measure the detector.

    python -m doc_extract.eval run --baseline pattern
    python -m doc_extract.eval run --baseline noisy --rate 0.15 --out results/noisy-015
    python -m doc_extract.eval run --baseline claude --model claude-haiku-4-5 --out results/haiku
    python -m doc_extract.eval score  --run results/pattern
    python -m doc_extract.eval detect --run results/pattern

`run` writes `predictions.jsonl`, `run.meta.json` and `report.md` into the output directory. `score`
recomputes the report from a directory that already has the first two, which is what makes a paid
run re-scorable for free after a change to the metric. `detect` reads the same two files and asks
the project's own question of them — whether the invariants predict the errors — writing
`detector.md` beside them.

Both readings therefore come from one committed artifact and neither needs the model again. The
model a run used is `--model`, and it is recorded in `run.meta.json`: two models over the same
corpus are two directories, not two baselines.

The four offline baselines need no key and no network. `--baseline claude` does, costs money, and
therefore refuses to start without `--yes`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from doc_extract.eval import dataset, detector_report, predictions, report, run
from doc_extract.eval.aggregate import CoverageError
from doc_extract.eval.baselines import BY_NAME
from doc_extract.eval.corrupt import DEFAULT_RATE
from doc_extract.eval.dataset import Case, Corpus, CorpusError
from doc_extract.eval.predictions import Prediction
from doc_extract.extract.pipeline import (
    DEFAULT_CONFIG,
    DEFAULT_MODEL,
    EXTRACTION_MAX_TOKENS,
    REPAIR_MAX_TOKENS,
    ExtractionConfig,
)
from doc_extract.schema.invariants import Severity

DEFAULT_CORPUS = Path("data/synthetic")
DEFAULT_RESULTS = Path("results")

#: The detector study, written beside the predictions it was computed from.
DETECTOR_NAME = "detector.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="doc_extract.eval", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    runner = commands.add_parser("run", help="predict with one baseline, then score")
    runner.add_argument("--baseline", required=True, choices=sorted(BY_NAME))
    runner.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    runner.add_argument("--out", type=Path, default=None,
                        help="output directory (default: results/<baseline>)")
    runner.add_argument("--tier", action="append", default=[],
                        help="restrict to one tier; may be repeated. Implies a partial report")
    runner.add_argument("--limit", type=int, default=None,
                        help="score only the first N documents. Implies a partial report")
    runner.add_argument("--allow-partial", action="store_true",
                        help="report on a subset deliberately; the report records that it is one")
    runner.add_argument("--model", default=DEFAULT_MODEL, help=f"default: {DEFAULT_MODEL}")
    runner.add_argument("--max-tokens", type=int, default=EXTRACTION_MAX_TOKENS)
    runner.add_argument("--repair-max-tokens", type=int, default=REPAIR_MAX_TOKENS)
    runner.add_argument("--max-repairs", type=int, default=DEFAULT_CONFIG.max_repairs)
    runner.add_argument("--effort", default=None, help="reasoning effort, passed through when set")
    runner.add_argument("--rate", type=float, default=DEFAULT_RATE,
                        help=f"corruption rate for the noisy oracle (default: {DEFAULT_RATE})")
    runner.add_argument("--quiet", action="store_true", help="no per-document line")
    runner.add_argument("--yes", action="store_true",
                        help="confirm a baseline that calls a paid API over the network")

    scorer = commands.add_parser("score", help="recompute a report from predictions on disk")
    scorer.add_argument("--run", type=Path, required=True, help="a directory written by `run`")
    scorer.add_argument("--corpus", type=Path, default=None,
                        help="override the corpus recorded in run.meta.json")
    scorer.add_argument("--allow-partial", action="store_true")

    detect = commands.add_parser(
        "detect", help="measure the invariants as an error detector over predictions on disk"
    )
    detect.add_argument("--run", type=Path, required=True, help="a directory written by `run`")
    detect.add_argument("--corpus", type=Path, default=None,
                        help="override the corpus recorded in run.meta.json")
    detect.add_argument("--allow-partial", action="store_true")

    args = parser.parse_args(argv)
    handlers = {"run": _run, "score": _score, "detect": _detect}
    try:
        return handlers[args.command](args)
    except (CorpusError, CoverageError) as error:
        print(f"error: {error}")
        return 2


def _run(args: argparse.Namespace) -> int:
    baseline = BY_NAME[args.baseline]
    if baseline.remote and not args.yes:
        print(
            f"the `{baseline.name}` baseline calls a model over the network and costs money.\n"
            "Re-run with --yes to confirm. ANTHROPIC_API_KEY is read from the environment."
        )
        return 2

    corpus = dataset.load(args.corpus)
    partial = bool(args.tier or args.limit)
    if partial:
        corpus = corpus.select(tiers=tuple(args.tier), limit=args.limit)

    config = ExtractionConfig(
        model=args.model,
        max_tokens=args.max_tokens,
        repair_max_tokens=args.repair_max_tokens,
        max_repairs=args.max_repairs,
        effort=args.effort,
    )
    options = {"rate": args.rate} if baseline.name == "noisy" else {}
    meta = run.meta(corpus, baseline, config=config, options=options)
    #: A baseline writes to a directory named for itself; a remote run writes to one named for the
    #: model, because the baseline is the same `claude` every time and the model is the variable.
    #: Two models over one corpus have to be two directories or the second silently overwrites the
    #: first — and comparing them is the whole reason for running more than one.
    out_dir = args.out or DEFAULT_RESULTS / (config.model if baseline.remote else baseline.name)

    print(f"{baseline.name}: {baseline.description}")
    print(f"  corpus  : {corpus.directory} ({len(corpus.cases)} documents)")
    print(f"  writing : {out_dir}")

    records = run.predict(
        corpus, baseline, config=config, options=options,
        progress=None if args.quiet else _progress,
    )
    run.write(out_dir, records, meta)
    return _report(corpus, records, meta, out_dir, allow_partial=args.allow_partial or partial)


def _score(args: argparse.Namespace) -> int:
    meta = predictions.read_meta(args.run / predictions.RUN_NAME)
    records = predictions.read(args.run / predictions.PREDICTIONS_NAME)
    corpus = dataset.load(args.corpus or Path(meta.corpus_dir))
    return _report(corpus, records, meta, args.run, allow_partial=args.allow_partial)


def _detect(args: argparse.Namespace) -> int:
    """Both severities, into one file, because they are two detectors over the same documents.

    Written beside the predictions rather than into a directory of its own: the study is a reading
    of that run, and a reader who has the numbers should be one `ls` away from the predictions they
    were computed from.
    """
    meta = predictions.read_meta(args.run / predictions.RUN_NAME)
    records = predictions.read(args.run / predictions.PREDICTIONS_NAME)
    corpus = dataset.load(args.corpus or Path(meta.corpus_dir))

    studies = [
        run.detect(corpus, records, severity=severity, allow_partial=args.allow_partial)
        for severity in Severity
    ]
    #: `as_posix`, not `str`: this file is committed, and a backslash would make the bytes differ
    #: between the machine that wrote it and the one that reviews the diff.
    body = "\n\n---\n\n".join(
        detector_report.render(study, run=meta, directory=args.run.as_posix())
        for study in studies
    )
    path = args.run / DETECTOR_NAME
    path.write_bytes(body.encode("utf-8"))

    print(f"{meta.baseline} — {meta.model}")
    print(f"  corpus  : {corpus.directory} ({len(corpus.cases)} documents)")
    print()
    for study in studies:
        for line in detector_report.summary_lines(study):
            print(f"  {line}")
        print()
    print(f"  report     : {path}")
    return 0


def _report(
    corpus: Corpus,
    records: tuple[Prediction, ...],
    meta: predictions.RunMeta,
    out_dir: Path,
    *,
    allow_partial: bool,
) -> int:
    summary = run.score(corpus, records, run=meta, allow_partial=allow_partial)
    path = out_dir / predictions.REPORT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(report.render(summary, predictions=records).encode("utf-8"))

    print()
    for line in report.summary_lines(summary):
        print(f"  {line}")
    print(f"  report     : {path}")
    return 0


def _progress(case: Case, record: Prediction) -> None:
    mark = "ok " if record.succeeded else record.failure
    notes = f"  [{len(record.notes)} injected]" if record.notes else ""
    print(f"  {case.doc_id:<24} {mark}{notes}")


if __name__ == "__main__":
    raise SystemExit(main())
