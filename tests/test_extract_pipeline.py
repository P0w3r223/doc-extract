"""The pipeline: the stage order, the failure taxonomy, and what a prediction has to record.

The model is scripted, so everything here is deterministic and offline. What is being tested is the
part that is this project's own — the fixed stage order, the repair loop it owns, and the fact that
a prediction comes back with a class, a `stop_reason` and the cost of *every* attempt, which is what
M4's metric rules require and what a scorer cannot reconstruct afterwards.

The headline is `test_a_perfect_reading_of_the_corpus_comes_back_as_the_gold`. It is the strongest
claim M3 can make without a model: whatever M4 later measures below that number belongs to the
model, not to the prompt, the schema or the parser.
"""

from __future__ import annotations

import dataclasses
import json
from decimal import Decimal

import pytest

from doc_extract.extract import pipeline, scripted, wire
from doc_extract.extract.client import LLMError, LLMRequest, Usage
from doc_extract.extract.pipeline import ExtractionConfig, extract
from doc_extract.extract.result import FailureClass, Stage
from doc_extract.source import document as source
from doc_extract.source.document import SourceDocument
from doc_extract.synth import render
from doc_extract.synth.build import build
from doc_extract.synth.corpus import documents
from doc_extract.synth.tiers import BY_NAME

SOURCE = SourceDocument(text="Faktura FV/2026/08/0001\nRazem 339,90", words=(), cells=(), pages=1)


def reply(text: str, **overrides) -> scripted.Reply:
    return dataclasses.replace(scripted.Reply(text=text), **overrides)


def payload(invoice, **overrides) -> str:
    return json.dumps({**wire.serialise(invoice), **overrides}, ensure_ascii=False)


# --------------------------------------------------------------------------- the happy path


def test_a_perfect_reading_of_the_corpus_comes_back_as_the_gold():
    """One document per tier, through the prompt, the wire format and the parser, unchanged."""
    for document in documents(per_tier=1):
        result = extract(SOURCE, scripted.oracle(document.invoice))
        assert result.succeeded, (document.doc_id, result.failure, result.attempts[-1].detail)
        assert result.invoice == document.invoice, document.doc_id
        assert result.failure is FailureClass.NONE
        assert len(result.attempts) == 1
        assert result.repairs == 0


def test_the_whole_chain_runs_on_a_rendered_page():
    """PDF bytes to `Invoice`, through every stage M3 adds, with only the model faked.

    The stub `SOURCE` above keeps the other tests fast and readable; this one is the reason to
    believe them. A real page is two orders of magnitude larger, carries diacritics, wraps its rows
    and interleaves its columns, and the prompt is built from it here rather than from a sentence.
    """
    built = build(BY_NAME["mixed_rates"], seed=21_000, doc_id="e2e", template="classic")
    document = source.read(render.render(built).data)
    client = scripted.oracle(built.invoice)

    result = extract(document, client)

    assert result.succeeded
    assert result.invoice == built.invoice
    assert "18 344,46" in client.requests[0].user, "the page's own total reached the prompt"
    assert document.text in client.requests[0].user


def test_the_request_carries_the_schema_the_document_and_nothing_of_the_caller_s_state(invoice):
    client = scripted.oracle(invoice)
    extract(SOURCE, client, config=ExtractionConfig(model="claude-opus-5", max_tokens=1234))
    request = client.requests[0]
    assert request.model == "claude-opus-5"
    assert request.max_tokens == 1234
    assert request.schema == wire.invoice_schema()
    assert SOURCE.text in request.user
    assert SOURCE.text not in request.system


def test_a_request_has_no_place_to_put_a_sampling_temperature():
    """Recorded as a test because it is an API constraint, not a preference.

    The current Opus and Sonnet models reject `temperature`, `top_p` and `top_k` outright, so a
    field for one would be a field that makes every request fail with a 400.
    """
    assert "temperature" not in {field.name for field in dataclasses.fields(LLMRequest)}


def test_money_never_passes_through_a_float(invoice):
    """Eighteen significant digits, sent as a JSON *number*, recovered exactly.

    A float would round this to 1234567890.1234568. The wire format asks for strings, so this path
    should never occur — which is precisely why it is worth pinning: it proves the parse is
    `Decimal`-native rather than merely usually given strings.
    """
    exact = Decimal("1234567890.12345678")
    body = payload(invoice).replace(
        f'"unit_price_net": "{invoice.lines[0].unit_price_net}"',
        '"unit_price_net": 1234567890.12345678',
    )
    assert "1234567890.12345678" in body and '"1234567890' not in body
    result = extract(SOURCE, scripted.ScriptedClient(reply(body)))
    assert result.succeeded, result.attempts[-1].detail
    assert result.invoice.lines[0].unit_price_net == exact


# --------------------------------------------------------------------------- the repair loop


def test_a_schema_error_is_repaired_with_the_validator_s_own_errors(invoice):
    client = scripted.ScriptedClient(
        reply(payload(invoice, currency="XYZ")), scripted.as_reply(invoice)
    )
    result = extract(SOURCE, client)

    assert result.succeeded
    assert result.invoice == invoice
    assert [attempt.stage for attempt in result.attempts] == [Stage.EXTRACT, Stage.REPAIR]
    assert result.attempts[0].failure is FailureClass.SCHEMA_INVALID
    assert "currency" in result.attempts[0].detail
    assert "TKodWaluty" in client.requests[1].user


def test_the_repair_has_its_own_token_budget(invoice):
    """One budget for two stages would hide which stage ran out — an M4 metric rule."""
    client = scripted.ScriptedClient(
        reply(payload(invoice, currency="XYZ")), scripted.as_reply(invoice)
    )
    extract(SOURCE, client, config=ExtractionConfig(max_tokens=8000, repair_max_tokens=2000))
    assert [request.max_tokens for request in client.requests] == [8000, 2000]


def test_the_repair_is_bounded(invoice):
    broken = reply(payload(invoice, currency="XYZ"))
    client = scripted.ScriptedClient(broken, broken, broken)
    result = extract(SOURCE, client, config=ExtractionConfig(max_repairs=1))

    assert not result.succeeded
    assert len(result.attempts) == 2
    assert client.remaining == 1, "the pipeline asked more often than max_repairs allows"


def test_no_repair_is_attempted_when_none_was_asked_for(invoice):
    client = scripted.ScriptedClient(reply(payload(invoice, currency="XYZ")))
    result = extract(SOURCE, client, config=ExtractionConfig(max_repairs=0))
    assert len(result.attempts) == 1
    assert result.failure is FailureClass.SCHEMA_INVALID


def test_cost_is_reported_over_every_attempt_including_the_failed_one(invoice):
    """Reporting only the successful call makes a pipeline that repairs half its documents look
    as cheap as one that never does."""
    client = scripted.ScriptedClient(
        reply(payload(invoice, currency="XYZ"), usage=Usage(input_tokens=100, output_tokens=20)),
        dataclasses.replace(
            scripted.as_reply(invoice), usage=Usage(input_tokens=140, output_tokens=25)
        ),
    )
    result = extract(SOURCE, client)
    assert result.usage == Usage(input_tokens=240, output_tokens=45)
    assert result.repairs == 1


# --------------------------------------------------------------------------- the failure taxonomy


@pytest.mark.parametrize(
    ("body", "stop_reason", "expected", "repairable"),
    [
        ("", "refusal", FailureClass.REFUSED, False),
        ('{"kind":', "max_tokens", FailureClass.TRUNCATED, False),
        ("   ", "end_turn", FailureClass.EMPTY, False),
        ("not json at all", "end_turn", FailureClass.MALFORMED_JSON, True),
        ("[1, 2, 3]", "end_turn", FailureClass.MALFORMED_JSON, True),
        ('{"kind": "VAT"}', "end_turn", FailureClass.SCHEMA_INVALID, True),
    ],
)
def test_each_failure_is_named_and_only_the_repairable_ones_are_retried(
    body, stop_reason, expected, repairable, invoice
):
    """A refusal and a truncation carry a body too, which is why `stop_reason` is read first."""
    client = scripted.ScriptedClient(
        reply(body, stop_reason=stop_reason), scripted.as_reply(invoice)
    )
    result = extract(SOURCE, client)

    assert result.attempts[0].failure is expected
    assert result.attempts[0].stop_reason == stop_reason
    assert result.succeeded is repairable
    assert (client.remaining == 0) is repairable


def test_a_transport_failure_is_a_result_and_not_an_exception():
    client = scripted.ScriptedClient(LLMError("no network"))
    result = extract(SOURCE, client)

    assert not result.succeeded
    assert result.failure is FailureClass.CLIENT_ERROR
    assert "no network" in result.attempts[0].detail
    assert result.usage == Usage()


def test_a_failed_extraction_still_records_what_was_asked_and_what_came_back(invoice):
    """"It didn't work" is not a finding; a class, a `stop_reason` and a detail are."""
    client = scripted.ScriptedClient(
        reply("not json", stop_reason="end_turn"), reply("still not json", stop_reason="end_turn")
    )
    result = extract(SOURCE, client)

    assert result.invoice is None
    assert [attempt.stage for attempt in result.attempts] == [Stage.EXTRACT, Stage.REPAIR]
    assert all(attempt.failure is FailureClass.MALFORMED_JSON for attempt in result.attempts)
    assert all(attempt.detail for attempt in result.attempts)


def test_the_model_that_answered_is_recorded_rather_than_the_one_that_was_asked(invoice):
    """A refusal can be served by a fallback, and a metric reporting the request is reporting us."""
    answered = dataclasses.replace(scripted.as_reply(invoice), model="claude-opus-4-8")
    result = extract(SOURCE, scripted.ScriptedClient(answered),
                     config=ExtractionConfig(model="claude-opus-5"))
    assert result.attempts[0].model == "claude-opus-4-8"


def test_the_error_report_sent_back_to_the_model_is_bounded(invoice):
    """A malformed answer can raise one error per line item; a repair prompt is not a transcript."""
    lines = [{"line_no": index, "vat_rate": "99"} for index in range(1, 60)]
    client = scripted.ScriptedClient(
        reply(payload(invoice, lines=lines)), scripted.as_reply(invoice)
    )
    extract(SOURCE, client)

    reported = client.requests[1].user
    assert reported.count("TStawkaPodatku") == pipeline.MAX_REPORTED_ERRORS
    assert "... and 39 more" in reported
