"""End to end, on a corpus generated for the test: predict, write, score, and score again.

This is the module that would catch the failures the individual units cannot: a baseline wired to
the wrong client, a report computed over documents that were never read, a prediction file that
cannot reproduce the numbers it was written for. It builds a real (small) corpus, renders real PDFs,
and reads them back through the same code a full run uses — with no model, no key and no network.
"""

from __future__ import annotations

import dataclasses

import pytest

from doc_extract.eval import dataset, predictions, report, run, selective_report
from doc_extract.eval.aggregate import CoverageError
from doc_extract.eval.baselines import BY_NAME as BASELINES
from doc_extract.eval.dataset import CorpusError
from doc_extract.schema.invariants import Severity
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


def test_the_detector_study_refuses_a_subset_nobody_declared(built):
    """The easiest number in this project to inflate, and the check that stops it.

    Dropping the documents a detector missed raises its recall. So `detect` asserts coverage the
    same way `score` does, by the same code, and a caller who genuinely wants a subset has to say
    so — after which the study is over a subset and cannot be quoted as one over the corpus.
    """
    corpus, records, _, _ = _run(built, "noisy", rate=1.0)
    short = records[:1]

    with pytest.raises(CoverageError, match="scored 1 of the 2 documents"):
        run.detect(corpus, short)

    study = run.detect(corpus, short, allow_partial=True)
    assert study.counts.documents == 1


def test_the_detector_sees_the_injected_errors_the_noisy_oracle_made(built):
    """End to end: corrupt a document, and the study reports both the verdict and the kind."""
    corpus, records, _, _ = _run(built, "noisy", rate=1.0)
    study = run.detect(corpus, records)

    assert study.counts.judged == len(records)
    assert study.counts.true_positive, "an all-corruptions run must trip a hard rule somewhere"
    assert {row.kind for row in study.kinds}, "the injected kinds must reach the study"


def test_the_heuristic_half_catches_the_kind_the_arithmetic_cannot(built):
    """Why `year_misread` exists: a heuristic rate that was zero on every run measures nothing.

    Asserted end to end rather than on `invariants` alone, because the claim is about the *study* —
    a kind can break a heuristic rule and still never reach the table if the severity split, the
    per-kind attribution or the note parsing drops it on the way.
    """
    corpus, records, _, _ = _run(built, "noisy", rate=1.0)
    study = run.detect(corpus, records, severity=Severity.HEURISTIC)
    rows = {row.kind: row for row in study.kinds}

    assert study.counts.true_positive, "the heuristic rules must fire on an all-corruptions run"
    assert study.counts.false_positive == 0
    assert rows["year_misread"].marginal_fired == rows["year_misread"].marginal_documents
    assert not rows["year_misread"].out_of_scope
    assert rows["total_transposed"].out_of_scope, "an arithmetic kind is not asked of a heuristic"


def test_a_kind_the_other_severity_owns_is_labelled_rather_than_counted_as_a_miss(built):
    """`not asked` and `missed` both print a zero, and only one of them is a detector failure."""
    corpus, records, _, _ = _run(built, "noisy", rate=1.0)
    hard = {row.kind: row for row in run.detect(corpus, records).kinds}

    assert hard["year_misread"].out_of_scope
    assert not hard["year_misread"].expected_invisible, "a rule does see it — just not a hard one"
    #: `name_truncated` rather than `date_shifted` for the invisible half of the claim: the two are
    #: the same declaration, and `date_shifted` is the kind that loses the sale-date collision at a
    #: rate of one, so it has no row to read here.
    assert hard["name_truncated"].expected_invisible
    assert not hard["name_truncated"].out_of_scope, "nothing owns it, so nobody is off the hook"
    assert not hard["total_transposed"].out_of_scope


def test_an_extraction_with_no_table_is_invisible_to_every_hard_rule(built):
    """`stripped` is the control for the one heuristic no corruption is allowed to produce.

    Every hard rule needs two figures to compare, so an answer carrying only the total leaves them
    nothing to run on: they are silent on a document that is wrong in most of its scored fields.
    That silence is a property of the rule set worth demonstrating rather than asserting in prose.
    """
    corpus, records, summary, _ = _run(built, "stripped")

    assert summary.extracted == 2, "a degenerate reading is still a well-formed invoice"
    assert summary.exact == 0
    assert all("stripped" in note for record in records for note in record.notes)

    hard = run.detect(corpus, records)
    assert hard.counts.prevalence == 1.0
    assert hard.counts.true_positive == 0, "no hard rule can see a table that is not there"

    heuristic = run.detect(corpus, records, severity=Severity.HEURISTIC)
    assert heuristic.counts.recall == 1.0
    assert heuristic.counts.false_positive == 0


def test_the_gate_cannot_see_what_a_reading_never_asserted(built):
    """A limit the curve already discloses, made concrete by the arm that maximises it.

    `stripped` drops most of the scored fields and every value it *does* assert is correct, so the
    gate accepts all of them and leaks nothing — a perfect-looking curve over a reading that lost
    the invoice. Coverage is over asserted values, and no signal here separates "correctly absent"
    from "silently dropped". The count of what was never asserted is the only thing that says so.
    """
    corpus, records, _, meta = _run(built, "stripped")
    curve = run.gate(corpus, records)

    assert curve.missed > curve.assessed, "most of the invoice is gone, and only `missed` says so"
    assert curve.wrong == 0, "every value it did assert is correct — which is the trap"
    assert all(point.leaked == 0 for point in curve.points)
    assert str(curve.missed) in selective_report.render(curve, run=meta)


def test_a_perfect_reading_gives_the_detector_nothing_to_do(built):
    """The oracle is the control: no error, therefore no detection, therefore no rate."""
    corpus, records, _, _ = _run(built, "oracle")
    study = run.detect(corpus, records)

    assert study.counts.true_negative == len(records)
    assert study.counts.prevalence == 0.0
    assert study.counts.recall is None, "no wrong documents means recall has no denominator"
    assert study.counts.false_positive == 0


def test_the_gate_refuses_a_subset_nobody_declared(built):
    """`gate` carries the same coverage guard as `score` and `detect`, by the same code."""
    corpus, records, _, _ = _run(built, "noisy", rate=1.0)

    with pytest.raises(CoverageError, match="scored 1 of the 2 documents"):
        run.gate(corpus, records[:1])

    assert run.gate(corpus, records[:1], allow_partial=True).assessed >= 0


def test_the_gate_reports_everything_it_cannot_judge(built):
    """Three exclusions, each counted rather than dropped — the failure the metric rules forbid.

    A value the model never asserted, a value grounding declines to ask about, and a document that
    produced no invoice: all three leave the curve's denominator, and a curve whose exclusions are
    invisible is a metric over a subset nobody noticed.
    """
    corpus, records, _, _ = _run(built, "oracle")
    curve = run.gate(corpus, records)

    assert curve.without_prediction == 0
    assert curve.missed == 0
    assert curve.unassessable > 0, "`kind` is asserted on every document and never groundable"
    assert curve.points[-1].total == curve.assessed


def test_the_gate_accepts_a_perfect_reading_and_lets_nothing_leak(built):
    """The oracle's values are all on the page, so every one of them should clear the gate."""
    corpus, records, _, _ = _run(built, "oracle")
    curve = run.gate(corpus, records)

    assert curve.wrong == 0
    assert curve.points[0].coverage == 1.0, "a perfect reading is entirely high-confidence"
    assert all(point.leaked == 0 for point in curve.points)


def test_the_gate_counts_a_document_that_produced_no_invoice(built):
    """Not a leak and not a catch: no field of it was ever assessed."""
    corpus, records, _, _ = _run(built, "oracle")
    blinded = (dataclasses.replace(records[0], invoice=None), *records[1:])
    curve = run.gate(corpus, blinded)

    assert curve.without_prediction == 1
    assert {row.doc_id for row in curve.judged} == {case.doc_id for case in corpus.cases[1:]}


def test_the_gate_renders_with_what_the_curve_cannot_see_above_the_tables(built):
    corpus, records, _, meta = _run(built, "oracle")
    rendered = selective_report.render(run.gate(corpus, records), run=meta)

    assert "| asserted but not assessable |" in rendered
    assert "| gold values never asserted |" in rendered
    assert "Coverage is over the values the model asserted" in rendered
