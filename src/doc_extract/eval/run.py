"""One baseline over one corpus: predict, write, score. The only module here that touches a disk.

The order is deliberate and the split is the whole design. `predict` produces prediction records and
`write` puts them on disk **before** anything is scored, so a run that dies in the scorer — or a run
that cost money — has still kept what the model said. `score` then reads gold and predictions and
computes counts, and it can be run again tomorrow, on the committed file, without the model.

That separation is what makes the metric rules enforceable rather than aspirational. Coverage is
asserted against the manifest at scoring time, not at prediction time, so a partial run can be
recorded, seen to be partial, and refused as a headline number.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

from doc_extract.eval import predictions as prediction_file
from doc_extract.eval import scorer
from doc_extract.eval.aggregate import Report, Scored, summarise
from doc_extract.eval.baselines import Baseline, Task
from doc_extract.eval.dataset import Case, Corpus
from doc_extract.eval.predictions import Prediction, RunMeta
from doc_extract.extract import pipeline
from doc_extract.extract.pipeline import DEFAULT_CONFIG, ExtractionConfig
from doc_extract.extract.result import FailureClass

#: Called after each document, for a CLI that wants to say something while a paid run is going.
Progress = Callable[[Case, Prediction], None]


def predict(
    corpus: Corpus,
    baseline: Baseline,
    *,
    config: ExtractionConfig = DEFAULT_CONFIG,
    options: Mapping[str, Any] | None = None,
    progress: Progress | None = None,
) -> tuple[Prediction, ...]:
    """Run one baseline over every document of a corpus, in manifest order.

    One page is held at a time: `Case.source()` reads and verifies its PDF, the pipeline answers,
    and the record keeps the answer rather than the page. A hash mismatch raises rather than being
    recorded — a prediction made on bytes the manifest does not describe is not a prediction about
    the corpus the report names.
    """
    return tuple(_predict(corpus, baseline, config=config, options=options, progress=progress))


def _predict(
    corpus: Corpus,
    baseline: Baseline,
    *,
    config: ExtractionConfig,
    options: Mapping[str, Any] | None,
    progress: Progress | None,
) -> Iterator[Prediction]:
    for case in corpus.cases:
        #: Read once. `Case.source()` verifies the PDF's hash and re-parses its geometry, and doing
        #: that twice per document would double the cost of the one part of a run that is slow.
        source = case.source()
        prepared = baseline.prepare(Task(
            doc_id=case.doc_id,
            gold=case.gold(),
            source=source,
            seed=case.seed,
            options=dict(options or {}),
        ))
        extraction = pipeline.extract(source, prepared.client, config=config)
        record = prediction_file.record(
            extraction,
            doc_id=case.doc_id,
            tier=case.tier,
            template=case.template,
            pdf_sha256=case.pdf_sha256,
            notes=prepared.notes,
        )
        if progress is not None:
            progress(case, record)
        yield record


def score(
    corpus: Corpus,
    records: Sequence[Prediction],
    *,
    run: RunMeta,
    allow_partial: bool = False,
) -> Report:
    """Judge recorded predictions against the corpus's gold, then count.

    Predictions with no matching document are dropped *and* reported: they show up in
    `coverage.unexpected`, which is a coverage failure rather than a silent skip. Scoring them
    against nothing is impossible; letting them pass unnoticed is what the rule forbids.
    """
    by_id = {case.doc_id: case for case in corpus.cases}
    scored = [
        Scored(prediction=record, score=_judge(by_id[record.doc_id], record))
        for record in records
        if record.doc_id in by_id
    ]
    scored.extend(
        Scored(prediction=record, score=_orphan(record))
        for record in records
        if record.doc_id not in by_id
    )
    return summarise(scored, run=run, expected=corpus.expected, allow_partial=allow_partial)


def _judge(case: Case, record: Prediction) -> scorer.DocumentScore:
    return scorer.judge(
        case.gold(),
        record.parse(),
        doc_id=case.doc_id,
        tier=case.tier,
        template=case.template,
        failure=FailureClass(record.failure),
    )


def _orphan(record: Prediction) -> scorer.DocumentScore:
    """A prediction for a document the corpus does not contain: no gold, therefore no outcomes."""
    return scorer.DocumentScore(
        doc_id=record.doc_id,
        tier=record.tier,
        template=record.template,
        failure=FailureClass(record.failure),
        predicted=record.succeeded,
        results=(),
    )


def meta(
    corpus: Corpus,
    baseline: Baseline,
    *,
    config: ExtractionConfig,
    options: Mapping[str, Any] | None = None,
    started_at: str | None = None,
) -> RunMeta:
    """The run header: what answered, on what, with which budgets, over which corpus."""
    return RunMeta(
        baseline=baseline.name,
        model=config.model if baseline.remote else baseline.name,
        corpus_dir=str(corpus.directory),
        documents=len(corpus.cases),
        max_tokens=config.max_tokens,
        repair_max_tokens=config.repair_max_tokens,
        max_repairs=config.max_repairs,
        effort=config.effort,
        started_at=started_at or now(),
        corpus=dict(corpus.provenance),
        options={"sees": baseline.sees, **dict(options or {})},
    )


def now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def write(out_dir: Path, records: Sequence[Prediction], run: RunMeta) -> Path:
    """Predictions and the run header, side by side, in a directory named for the run."""
    path = out_dir / prediction_file.PREDICTIONS_NAME
    prediction_file.write(records, path)
    prediction_file.write_meta(run, out_dir / prediction_file.RUN_NAME)
    return path
