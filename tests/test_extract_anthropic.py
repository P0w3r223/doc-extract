"""The one module that talks to a real model, tested without talking to one.

`anthropic_client` was the last module here with no tests, and the excuse was that it needs the
network. It does not: it is a *mapping* — `LLMRequest` onto one SDK call and the reply back onto
`LLMResponse` — and a mapping can be checked against a stub that records what it was asked. What
cannot be checked here is whether the API accepts the payload; that is what the first real call
answers, and it is the reason the request shape is asserted rather than eyeballed.

The stubs deliberately mimic the SDK's *object* interface (attributes, not dict keys) and nothing
else, so a test passes only if the adapter reads the reply the way the SDK actually presents it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from doc_extract.extract.anthropic_client import AnthropicClient, first_text, usage_of
from doc_extract.extract.client import LLMError, LLMRequest


@dataclass
class _Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class _Block:
    type: str
    text: str = ""
    thinking: str = ""


@dataclass
class _Message:
    content: list[_Block]
    stop_reason: str | None = "end_turn"
    usage: _Usage = field(default_factory=_Usage)
    model: str = "claude-opus-5"


class _Messages:
    def __init__(self, reply: _Message | Exception) -> None:
        self._reply = reply
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _Message:
        self.calls.append(kwargs)
        if isinstance(self._reply, Exception):
            raise self._reply
        return self._reply


class _SDK:
    def __init__(self, reply: _Message | Exception) -> None:
        self.messages = _Messages(reply)


def _request(**over: Any) -> LLMRequest:
    return LLMRequest(
        model=over.pop("model", "claude-opus-5"),
        system=over.pop("system", "SYSTEM"),
        user=over.pop("user", "USER"),
        schema=over.pop("schema", {"type": "object"}),
        max_tokens=over.pop("max_tokens", 16000),
        **over,
    )


def _sent(reply: _Message | Exception, request: LLMRequest):
    sdk = _SDK(reply)
    response = AnthropicClient(sdk).complete(request)
    return sdk.messages.calls[0], response


def test_the_document_never_reaches_the_system_prompt():
    """The trust rule, asserted at the boundary rather than only in the prompt module."""
    call, _ = _sent(_Message(content=[_Block("text", text="{}")]), _request(user="INVOICE TEXT"))

    assert call["system"][0]["text"] == "SYSTEM"
    assert "INVOICE TEXT" not in call["system"][0]["text"]
    assert call["messages"] == [{"role": "user", "content": "INVOICE TEXT"}]


def test_the_system_prompt_is_sent_as_a_cached_block():
    """One prompt against a hundred documents: the constant prefix is the part worth caching."""
    call, _ = _sent(_Message(content=[_Block("text", text="{}")]), _request())

    (block,) = call["system"]
    assert block["type"] == "text"
    assert block["cache_control"] == {"type": "ephemeral"}


def test_the_schema_travels_as_structured_output_and_not_as_a_tool():
    """A tool input arrives parsed by the SDK, and an amount that has been through someone else's
    `json.loads` has been through a float. The raw body has to stay ours."""
    schema = {"type": "object", "properties": {"total_gross": {"type": "string"}}}
    call, _ = _sent(_Message(content=[_Block("text", text="{}")]), _request(schema=schema))

    assert call["output_config"]["format"] == {"type": "json_schema", "schema": schema}
    assert "tools" not in call
    assert "effort" not in call["output_config"], "unset effort leaves the API's own default alone"


def test_effort_is_passed_inside_output_config_when_set():
    call, _ = _sent(_Message(content=[_Block("text", text="{}")]), _request(effort="medium"))
    assert call["output_config"]["effort"] == "medium"


def test_no_sampling_parameters_are_sent():
    """Current Opus and Sonnet models reject `temperature`, `top_p` and `top_k` outright."""
    call, _ = _sent(_Message(content=[_Block("text", text="{}")]), _request())
    assert not {"temperature", "top_p", "top_k"} & set(call)


def test_the_answer_is_read_past_a_thinking_block():
    """The models think before answering, so `content[0]` is not the answer.

    Indexing blindly would hand the pipeline an empty string and have it report that the model said
    nothing — on every single document, and only once a real model was finally called.
    """
    message = _Message(
        content=[_Block("thinking", thinking="reasoning"), _Block("text", text='{"kind": "VAT"}')],
        usage=_Usage(input_tokens=2000, output_tokens=700, cache_read_input_tokens=900),
        model="claude-opus-5",
    )
    _, response = _sent(message, _request())

    assert response.text == '{"kind": "VAT"}'
    assert response.stop_reason == "end_turn"
    assert response.model == "claude-opus-5"
    assert response.usage.output_tokens == 700
    assert response.usage.cache_read_input_tokens == 900


def test_a_refusal_is_a_response_and_not_an_error():
    """A declined request is a content outcome the pipeline classifies, not a transport failure."""
    _, response = _sent(
        _Message(content=[], stop_reason="refusal"), _request()
    )
    assert response.stop_reason == "refusal"
    assert response.text == ""


def test_a_missing_stop_reason_becomes_an_empty_string():
    _, response = _sent(_Message(content=[_Block("text", text="{}")], stop_reason=None), _request())
    assert response.stop_reason == ""


def test_any_sdk_exception_becomes_an_llm_error():
    """Deliberately broad: authentication, rate limits and connection loss are all "no answer"."""
    with pytest.raises(LLMError, match="the Anthropic API call failed"):
        _sent(RuntimeError("connection reset"), _request())


def test_the_model_that_answered_is_reported_and_not_the_one_requested():
    _, response = _sent(
        _Message(content=[_Block("text", text="{}")], model="claude-opus-4-8"),
        _request(model="claude-opus-5"),
    )
    assert response.model == "claude-opus-4-8"


def test_first_text_and_usage_are_total_over_odd_replies():
    assert first_text([]) == ""
    assert first_text([_Block("thinking", thinking="only thinking")]) == ""
    assert usage_of(_Usage()) == usage_of(_Usage())
    #: A usage object missing the cache fields reads as zero rather than raising — they are absent
    #: from a reply that never touched the cache.
    assert usage_of(object()).input_tokens == 0
