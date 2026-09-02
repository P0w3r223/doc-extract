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

from doc_extract.attack import outcome
from doc_extract.attack.suite import Assignment
from doc_extract.decide import confidence
from doc_extract.eval import detector, scorer, selective
from doc_extract.eval import predictions as prediction_file
from doc_extract.eval.aggregate import (
    Coverage,
    CoverageError,
    Report,
    Scored,
    coverage_message,
    summarise,
)
from doc_extract.eval.baselines import Baseline, Task
from doc_extract.eval.dataset import Case, Corpus
from doc_extract.eval.predictions import Prediction, RunMeta
from doc_extract.extract import pipeline
from doc_extract.extract.pipeline import DEFAULT_CONFIG, ExtractionConfig
from doc_extract.extract.result import FailureClass
from doc_extract.schema.invariants import Severity

#: Called after each document, for a CLI that wants to say something while a paid run is going.
Progress = Callable[[Case, Prediction], None]


def predict(
    corpus: Corpus,
    baseline: Baseline,
    *,
    config: ExtractionConfig = DEFAULT_CONFIG,
    options: Mapping[str, Any] | None = None,
    progress: Progress | None = None,
    vision: bool = False,
) -> tuple[Prediction, ...]:
    """Run one baseline over every document of a corpus, in manifest order.

    One page is held at a time: `Case.source()` reads and verifies its PDF, the pipeline answers,
    and the record keeps the answer rather than the page. A hash mismatch raises rather than being
    recorded — a prediction made on bytes the manifest does not describe is not a prediction about
    the corpus the report names.

    `vision` sends the page as images instead of as text. The baseline is unchanged by it — every
    offline one answers from the gold or from the text and ignores what was sent — which is the
    point: the modality is a property of the *request*, and putting it here rather than in a
    baseline of its own keeps the two arms comparable through one prompt, one repair loop and one
    failure taxonomy.
    """
    return tuple(_predict(
        corpus, baseline, config=config, options=options, progress=progress, vision=vision
    ))


def _predict(
    corpus: Corpus,
    baseline: Baseline,
    *,
    config: ExtractionConfig,
    options: Mapping[str, Any] | None,
    progress: Progress | None,
    vision: bool = False,
) -> Iterator[Prediction]:
    for case in corpus.cases:
        #: Read once, and hashed once. Both readings of a page — its text and its pixels — start
        #: from the same verified bytes, so a vision run does not open and re-hash every PDF twice
        #: to get them.
        data = case.pdf_bytes()
        source = case.source(data)
        prepared = baseline.prepare(Task(
            doc_id=case.doc_id,
            gold=case.gold(),
            source=source,
            seed=case.seed,
            options=dict(options or {}),
        ))
        extraction = pipeline.extract(
            source, prepared.client, config=config, images=case.images(data) if vision else ()
        )
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


def detect(
    corpus: Corpus,
    records: Sequence[Prediction],
    *,
    severity: Severity = Severity.HARD,
    allow_partial: bool = False,
) -> detector.Study:
    """The same predictions, judged as a detection problem rather than as a reading problem.

    Coverage is asserted here exactly as it is in `score`, and for a reason specific to this study:
    a detector's recall over a subset nobody noticed is the single easiest number to inflate, since
    dropping the documents it missed raises it. The check is the same one, by the same code, so it
    cannot drift apart from the scorer's.
    """
    by_id = {case.doc_id: case for case in corpus.cases}
    scored = tuple(record for record in records if record.doc_id in by_id)
    coverage = Coverage(
        expected=tuple(corpus.expected), scored=tuple(record.doc_id for record in scored)
    )
    if not coverage.complete and not allow_partial:
        raise CoverageError(coverage_message(coverage))

    return detector.summarise(
        (
            detector.verdict(
                _judge(by_id[record.doc_id], record),
                record.parse(),
                severity=severity,
                notes=record.notes,
            )
            for record in scored
        ),
        severity=severity,
    )


def gate(
    corpus: Corpus,
    records: Sequence[Prediction],
    *,
    allow_partial: bool = False,
) -> selective.Curve:
    """The routing gate, measured against gold as a coverage-accuracy curve.

    The one function in this module that re-reads the pages: grounding a value needs the document
    it came from, and a prediction file does not carry it. That is also why the corpus's hashes are
    verified on the way — a curve computed against different bytes than the prediction was made
    from would be measuring two documents at once.
    """
    by_id = {case.doc_id: case for case in corpus.cases}
    scored = tuple(record for record in records if record.doc_id in by_id)
    coverage = Coverage(
        expected=tuple(corpus.expected), scored=tuple(record.doc_id for record in scored)
    )
    if not coverage.complete and not allow_partial:
        raise CoverageError(coverage_message(coverage))

    rows: list[selective.Judged] = []
    #: Every exclusion is decided where the evidence is — inside `judge`, which holds the page's
    #: own verdict on each value. An earlier version counted the text-less ones here instead, by
    #: asking whether the document had any text and attributing the whole document to the answer.
    #: That worked only while grounding could not say so itself, and it counted values that were
    #: *in* the curve rather than excluded from it.
    excluded = selective.Excluded()
    without_prediction = 0
    for record in scored:
        invoice = record.parse()
        if invoice is None:
            without_prediction += 1
            continue
        case = by_id[record.doc_id]
        judged, lost = selective.judge(case.doc_id, case.gold(), invoice, case.source())
        rows.extend(judged)
        excluded += lost

    return selective.summarise(
        rows, missed=excluded.missed, unassessable=excluded.unassessable,
        without_prediction=without_prediction, without_text=excluded.without_text,
        wrong_unassessable=excluded.wrong_unassessable,
        wrong_without_text=excluded.wrong_without_text,
    )


def attacks(
    corpus: Corpus,
    records: Sequence[Prediction],
    assignments: Sequence[Assignment],
    *,
    allow_partial: bool = False,
) -> outcome.Study:
    """The same predictions again, read as M6 reads them: did the page's instructions work?

    Three sources have to line up — the corpus, the prediction file and the suite's join file — and
    the two ways they can fail to are reported rather than silently dropped. A prediction with no
    assignment is a document the suite did not attack; an assignment with no prediction is an attack
    nobody ran. Either one moves an attack success rate, and in the direction that flatters it.

    Like `gate`, this re-reads the pages: the routing column asks what M5's gate would have done
    with the answer, and grounding a value needs the page it claims to come from.
    """
    by_id = {case.doc_id: case for case in corpus.cases}
    scored = tuple(record for record in records if record.doc_id in by_id)
    coverage = Coverage(
        expected=tuple(corpus.expected), scored=tuple(record.doc_id for record in scored)
    )
    if not coverage.complete and not allow_partial:
        raise CoverageError(coverage_message(coverage))

    planned = {assignment.doc_id: assignment for assignment in assignments}
    judged = [
        _attacked(by_id[record.doc_id], record, planned[record.doc_id])
        for record in scored
        if record.doc_id in planned
    ]
    predicted = {record.doc_id for record in scored}
    return outcome.summarise(
        judged,
        unmatched=tuple(record.doc_id for record in scored if record.doc_id not in planned),
        missing=tuple(doc_id for doc_id in planned if doc_id not in predicted),
    )


def _attacked(case: Case, record: Prediction, assignment: Assignment) -> outcome.Outcome:
    invoice = record.parse()
    return outcome.judge(
        assignment,
        case.gold(),
        invoice,
        _judge(case, record),
        failure=FailureClass(record.failure),
        route=None if invoice is None else confidence.route(
            confidence.assess(case.source(), invoice)
        ),
    )


def _judge(case: Case, record: Prediction) -> scorer.DocumentScore:
    return scorer.judge(
        case.gold(),
        record.parse(),
        doc_id=case.doc_id,
        facets=case.facets,
        failure=FailureClass(record.failure),
    )


def _orphan(record: Prediction) -> scorer.DocumentScore:
    """A prediction for a document the corpus does not contain: no gold, therefore no outcomes."""
    return scorer.DocumentScore(
        doc_id=record.doc_id,
        facets=(("tier", record.tier), ("template", record.template)),
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
        #: `as_posix`, not `str`: this is committed, and `score`/`detect`/`gate` all default
        #: to reading it back as a path. A Windows separator makes every one of them fail
        #: on a POSIX checkout of the same repository.
        corpus_dir=corpus.directory.as_posix(),
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
