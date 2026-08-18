"""The prediction file has to survive a round trip exactly, or the committed numbers drift.

A report is recomputable from `predictions.jsonl` alone — that is what makes a paid run re-scorable
after a change to the metric, and it is only true if the file loses nothing on the way to disk and
nothing on the way back. Money is the part that would fail silently, so it is the part tested first.
"""

from __future__ import annotations

from decimal import Decimal

from doc_extract.eval import predictions
from doc_extract.extract.client import Usage
from doc_extract.extract.result import Attempt, Extraction, FailureClass, Stage


def _extraction(invoice, *attempts: Attempt) -> Extraction:
    return Extraction(invoice=invoice, attempts=attempts)


def _attempt(stage=Stage.EXTRACT, failure=FailureClass.NONE, output=120) -> Attempt:
    return Attempt(
        stage=stage, model="scripted", stop_reason="end_turn",
        usage=Usage(input_tokens=1000, output_tokens=output), failure=failure,
    )


def test_a_prediction_round_trips_through_the_file(tmp_path, invoice):
    record = predictions.record(
        _extraction(invoice, _attempt()),
        doc_id="clean-0000", tier="clean", template="classic", pdf_sha256="a" * 64,
    )
    path = tmp_path / predictions.PREDICTIONS_NAME
    predictions.write([record], path)

    (back,) = predictions.read(path)
    assert back == record
    assert back.parse() == invoice


def test_money_survives_the_file_exactly(tmp_path, invoice):
    """Through JSON as a string, back through the validator, still the same `Decimal`."""
    odd = invoice.model_copy(update={"total_gross": Decimal("12345678901.23")})
    path = tmp_path / predictions.PREDICTIONS_NAME
    predictions.write(
        [predictions.record(_extraction(odd, _attempt()), doc_id="d", tier="t", template="c",
                            pdf_sha256="b" * 64)],
        path,
    )
    (back,) = predictions.read(path)
    restored = back.parse()
    assert restored is not None
    assert restored.total_gross == Decimal("12345678901.23")


def test_every_attempt_is_recorded_with_its_own_tokens(invoice):
    record = predictions.record(
        _extraction(
            invoice,
            _attempt(failure=FailureClass.SCHEMA_INVALID, output=800),
            _attempt(stage=Stage.REPAIR, output=200),
        ),
        doc_id="d", tier="t", template="c", pdf_sha256="c" * 64,
    )
    assert len(record.attempts) == 2
    assert record.repairs == 1
    assert record.usage.output_tokens == 1000
    assert record.attempts[0].failure == FailureClass.SCHEMA_INVALID
    #: The class on the record is the outcome, which is `none` — the failed attempt was repaired.
    assert record.failure == FailureClass.NONE


def test_a_failed_extraction_records_no_invoice_but_keeps_its_reason(invoice):
    record = predictions.record(
        Extraction(invoice=None, attempts=(_attempt(failure=FailureClass.TRUNCATED),)),
        doc_id="d", tier="t", template="c", pdf_sha256="d" * 64,
    )
    assert record.invoice is None
    assert record.parse() is None
    assert predictions.failure_of(record) is FailureClass.TRUNCATED
    assert record.stop_reason == "end_turn"


def test_the_run_header_round_trips(tmp_path):
    meta = predictions.RunMeta(
        baseline="noisy", model="noisy", corpus_dir="data/synthetic", documents=108,
        max_tokens=8192, repair_max_tokens=4096, max_repairs=1,
        corpus={"corpus_seed": 20260818}, options={"sees": "the gold", "rate": 0.1},
    )
    path = tmp_path / predictions.RUN_NAME
    predictions.write_meta(meta, path)
    assert predictions.read_meta(path) == meta


def test_the_notes_carry_what_a_baseline_did_to_the_document(tmp_path, invoice):
    record = predictions.record(
        _extraction(invoice, _attempt()),
        doc_id="d", tier="t", template="c", pdf_sha256="e" * 64,
        notes=("vat_cent rate_totals[23].vat: 57.50 -> 57.51",),
    )
    path = tmp_path / predictions.PREDICTIONS_NAME
    predictions.write([record], path)
    (back,) = predictions.read(path)
    assert back.notes == record.notes
