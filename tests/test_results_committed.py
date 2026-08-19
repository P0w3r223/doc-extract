"""The committed reports must be what today's code renders from the committed predictions.

The README makes a load-bearing promise: *a number in either report is recomputable from the file
that produced it, without re-running anything*. That promise is only true while the files on disk
match the renderer, and it silently stopped being true once — a change to how a rate is formatted
went in without regenerating the twelve reports it changed, and nothing failed.

So this asserts it. Gold is rebuilt in memory from the corpus seed, exactly as `docs/build_index.py`
does, which is what lets the check run on a clean checkout where `data/synthetic/` is not committed.
A run over M6's attacked corpus is rebuilt the same way and stays covered: the suite's grid is a
pure function of the base corpus and of the parameters the run's own provenance block records, so
`suite.plan` reproduces the gold of an attacked document without the corpus being on disk.

`gate.md` and `attack.md` are the two reports this cannot cover, and for one reason: both carry a
column that comes from grounding, and grounding needs the rendered pages.
"""

from __future__ import annotations

import pathlib

import pytest

from doc_extract.attack import suite
from doc_extract.attack.payloads import BY_NAME as PAYLOADS
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
def golds():
    """A run's gold, keyed by document id, from the seed rather than from disk.

    Two shapes of corpus answer to the same call. A clean run is the base corpus; an attacked run is
    the grid the suite planned over it, which is a pure function of the base documents and of the
    `per_cell` / `payloads` / `placements` the run's provenance block records. Built once per
    distinct set of parameters and shared, because rendering the base corpus is the slow part.
    """
    base = list(documents())
    clean = {document.doc_id: document for document in base}
    planned: dict[tuple, dict] = {}

    def for_run(meta):
        corpus = meta.corpus
        if not corpus.get("attacked"):
            return clean
        key = (
            corpus["per_cell"],
            tuple(corpus["payloads"]),
            tuple(corpus["placements"]),
        )
        if key not in planned:
            per_cell, payload_names, placements = key
            planned[key] = {
                document.doc_id: document
                for document, _ in suite.plan(
                    per_cell=per_cell,
                    payloads=tuple(PAYLOADS[name] for name in payload_names),
                    placements=placements,
                    base=base,
                )
            }
        return planned[key]

    return for_run


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
def test_the_committed_score_report_is_what_the_renderer_produces(name, golds):
    directory, meta, records = _read(name)
    gold = golds(meta)
    summary = summarise(_scored(records, gold), run=meta, expected=list(gold))
    rendered = report.render(summary, predictions=records)

    committed = (directory / predictions.REPORT_NAME).read_text(encoding="utf-8")
    assert rendered == committed, (
        f"results/{name}/{predictions.REPORT_NAME} is stale — re-run "
        f"`python -m doc_extract.eval score --run results/{name}`"
    )


@pytest.mark.skipif(not RUNS, reason="no committed runs")
@pytest.mark.parametrize("name", RUNS)
def test_the_committed_detector_report_is_what_the_renderer_produces(name, golds):
    directory, meta, records = _read(name)
    scored = {item.score.doc_id: item.score for item in _scored(records, golds(meta))}

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
