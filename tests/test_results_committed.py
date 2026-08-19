"""The committed reports must be what today's code renders from the committed predictions.

The README makes a load-bearing promise: *a number in either report is recomputable from the file
that produced it, without re-running anything*. That promise is only true while the files on disk
match the renderer, and it silently stopped being true once — a change to how a rate is formatted
went in without regenerating the twelve reports it changed, and nothing failed.

So this asserts it. Gold is rebuilt in memory from the corpus seed, exactly as `docs/build_index.py`
does, which is what lets the check run on a clean checkout where `data/synthetic/` is not committed.
`gate.md` is the one report it cannot cover, because grounding needs the rendered pages.
"""

from __future__ import annotations

import pathlib

import pytest

from doc_extract.eval import detector, detector_report, predictions, report
from doc_extract.eval.aggregate import Scored, summarise
from doc_extract.eval.scorer import judge
from doc_extract.extract.result import FailureClass
from doc_extract.schema.invariants import Severity
from doc_extract.synth.corpus import DEFAULT_SEED, documents

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

RUNS = sorted(
    directory.name
    for directory in RESULTS.iterdir()
    if (directory / predictions.PREDICTIONS_NAME).exists()
) if RESULTS.is_dir() else []


@pytest.fixture(scope="module")
def gold():
    """The corpus's gold, from the seed rather than from disk. Slow once, then shared."""
    return {document.doc_id: document for document in documents()}


def _read(name: str):
    directory = RESULTS / name
    meta = predictions.read_meta(directory / predictions.RUN_NAME)
    if meta.corpus.get("corpus_seed") != DEFAULT_SEED:
        pytest.skip(f"{name} was scored on another corpus seed")
    return directory, meta, predictions.read(directory / predictions.PREDICTIONS_NAME)


def _scored(records, gold):
    return [
        Scored(
            prediction=record,
            score=judge(
                gold[record.doc_id].invoice,
                record.parse(),
                doc_id=record.doc_id,
                tier=gold[record.doc_id].tier,
                template=gold[record.doc_id].template,
                failure=FailureClass(record.failure),
            ),
        )
        for record in records
    ]


@pytest.mark.skipif(not RUNS, reason="no committed runs")
@pytest.mark.parametrize("name", RUNS)
def test_the_committed_score_report_is_what_the_renderer_produces(name, gold):
    directory, meta, records = _read(name)
    summary = summarise(_scored(records, gold), run=meta, expected=list(gold))
    rendered = report.render(summary, predictions=records)

    committed = (directory / predictions.REPORT_NAME).read_text(encoding="utf-8")
    assert rendered == committed, (
        f"results/{name}/{predictions.REPORT_NAME} is stale — re-run "
        f"`python -m doc_extract.eval score --run results/{name}`"
    )


@pytest.mark.skipif(not RUNS, reason="no committed runs")
@pytest.mark.parametrize("name", RUNS)
def test_the_committed_detector_report_is_what_the_renderer_produces(name, gold):
    directory, meta, records = _read(name)
    scored = {item.score.doc_id: item.score for item in _scored(records, gold)}

    body = "\n\n---\n\n".join(
        detector_report.render(
            detector.summarise(
                (
                    detector.verdict(
                        scored[record.doc_id], record.parse(),
                        severity=severity, notes=record.notes,
                    )
                    for record in records
                ),
                severity=severity,
            ),
            run=meta,
            directory=f"results/{name}",
        )
        for severity in Severity
    )

    committed = (directory / "detector.md").read_text(encoding="utf-8")
    assert body == committed, (
        f"results/{name}/detector.md is stale — re-run "
        f"`python -m doc_extract.eval detect --run results/{name}`"
    )
