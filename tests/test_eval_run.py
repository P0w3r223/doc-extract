"""End to end, on a corpus generated for the test: predict, write, score, and score again.

This is the module that would catch the failures the individual units cannot: a baseline wired to
the wrong client, a report computed over documents that were never read, a prediction file that
cannot reproduce the numbers it was written for. It builds a real (small) corpus, renders real PDFs,
and reads them back through the same code a full run uses — with no model, no key and no network.
"""

from __future__ import annotations

import pytest

from doc_extract.eval import dataset, predictions, report, run
from doc_extract.eval.aggregate import CoverageError
from doc_extract.eval.baselines import BY_NAME as BASELINES
from doc_extract.eval.dataset import CorpusError
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.tiers import BY_NAME as TIERS


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """Two documents, two tiers, rendered once for every test in this module."""
    directory = tmp_path_factory.mktemp("corpus")
    synth_corpus.generate(directory, per_tier=1, tiers=(TIERS["clean"], TIERS["mixed_rates"]))
    return directory


def _run(directory, name, **options):
    corpus = dataset.load(directory)
    baseline = BASELINES[name]
    records = run.predict(corpus, baseline, options=options)
    meta = run.meta(corpus, baseline, config=run.DEFAULT_CONFIG, options=options)
    return corpus, records, run.score(corpus, records, run=meta), meta


def test_the_oracle_scores_everything_right(built):
    """If a perfect reading does not score 100 %, the harness is wrong and so is every number."""
    _, records, summary, _ = _run(built, "oracle")

    assert summary.documents == 2
    assert summary.extracted == 2
    assert summary.exact == 2
    assert summary.overall.accuracy == 1.0
    assert summary.overall.support > 0
    assert all(record.succeeded for record in records)


def test_the_constant_baseline_is_the_floor_and_the_pattern_baseline_beats_it(built):
    """An ordering claim, and the reason B1 is in the set: it says what a field's prior is worth."""
    _, _, constant, _ = _run(built, "constant")
    _, _, patterned, _ = _run(built, "pattern")

    assert constant.overall.accuracy < patterned.overall.accuracy
    assert constant.exact == 0
    #: B1 still produces a well-formed invoice every time — being wrong is not being malformed.
    assert constant.extracted == 2


def test_the_noisy_oracle_records_what_it_broke(built):
    _, records, summary, _ = _run(built, "noisy", rate=1.0)
    notes = [note for record in records for note in record.notes]

    assert notes, "a rate of 1.0 has to inject something"
    assert summary.overall.accuracy < 1.0
    assert "Injected errors" in report.render(summary, predictions=records)


def test_the_report_is_recomputable_from_the_file_alone(built, tmp_path):
    """Why predictions are committed: a paid run can be re-scored after the metric changes."""
    corpus, records, first, meta = _run(built, "pattern")
    run.write(tmp_path, records, meta)

    from_disk = predictions.read(tmp_path / predictions.PREDICTIONS_NAME)
    header = predictions.read_meta(tmp_path / predictions.RUN_NAME)
    second = run.score(corpus, from_disk, run=header)

    assert from_disk == records
    assert second.overall == first.overall
    assert second.by_field == first.by_field


def test_scoring_a_subset_is_refused_unless_it_says_so(built):
    corpus = dataset.load(built)
    subset = corpus.select(tiers=("clean",))
    baseline = BASELINES["oracle"]
    records = run.predict(subset, baseline, options={})
    meta = run.meta(subset, baseline, config=run.DEFAULT_CONFIG)

    assert subset.expected == corpus.doc_ids, "a subset has to remember what it is a subset of"
    with pytest.raises(CoverageError):
        run.score(subset, records, run=meta)

    partial = run.score(subset, records, run=meta, allow_partial=True)
    assert partial.coverage.complete is False
    assert "Partial coverage" in report.render(partial)


def test_a_corpus_that_does_not_match_its_manifest_is_refused(built, tmp_path):
    """A run scored on bytes the manifest does not describe is a result nobody can reproduce."""
    directory = tmp_path / "tampered"
    directory.mkdir()
    for source in built.iterdir():
        (directory / source.name).write_bytes(source.read_bytes())

    victim = next(directory.glob("*.pdf"))
    victim.write_bytes(victim.read_bytes() + b"%tampered\n")

    with pytest.raises(CorpusError, match="not the one this run would report"):
        run.predict(dataset.load(directory), BASELINES["oracle"])


def test_the_run_header_records_what_the_baseline_was_allowed_to_see(built):
    _, _, _, meta = _run(built, "oracle")
    assert meta.options["sees"] == "the gold"
    assert meta.corpus["corpus_seed"] == synth_corpus.DEFAULT_SEED
    assert meta.max_tokens != meta.repair_max_tokens, "the two budgets are reported separately"


def test_every_baseline_runs_offline_and_produces_a_report(built):
    """The offline set is the whole of M4: no key, no network, no cost, and a report each."""
    for name, baseline in BASELINES.items():
        if baseline.remote:
            continue
        _, records, summary, _ = _run(built, name)
        rendered = report.render(summary, predictions=records)
        assert rendered.startswith(f"# {name}")
        assert "| support |" in rendered
