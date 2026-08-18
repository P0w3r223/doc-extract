"""The one place this project talks to a real model. Thin on purpose.

It maps `LLMRequest` onto a Messages API call and the reply back onto `LLMResponse`, and does
nothing else — no retry policy, no parsing, no interpretation of `stop_reason`. Those decisions live
in `pipeline`, where they are reachable by `ScriptedClient` and therefore by a test.

Four choices are worth their reasons:

**Structured output, not a tool call.** `output_config.format` returns the object as text, so the
raw body reaches `pipeline` and the JSON parse stays under this project's control. A tool call
arrives already parsed by the SDK, and an amount that has been through someone else's `json.loads`
has been through a float. That is the difference between `Decimal("1234.56")` and a number that no
longer round-trips — see `wire`.

**No `temperature`.** Current Opus and Sonnet models reject sampling parameters outright; sending
one is a 400, not a nudge.

**Thinking is left alone.** The current models think by default, and turning it off is a false
economy here: a model answering with thinking disabled occasionally writes what should be a
structured call into its visible text instead, which arrives as a body that does not parse. The
token budget covers thinking and answer together, which is why `pipeline`'s default is generous.

**The SDK is imported lazily.** M1 to M3 install and test with no `anthropic` package and no key;
dependency is an extra (`pip install -e ".[llm]"`), and reaching this module is the only thing that
requires it. The key is read by the SDK from the environment at call time and never touches code.
"""

from __future__ import annotations

from typing import Any

from doc_extract.extract.client import LLMError, LLMRequest, LLMResponse, Usage


class AnthropicClient:
    """An `LLMClient` backed by the Anthropic Messages API."""

    def __init__(self, client: Any | None = None) -> None:
        """Pass a client to inject one; leave it out and the SDK builds its own on first use."""
        self._client = client

    def complete(self, request: LLMRequest) -> LLMResponse:
        client = self._client if self._client is not None else _build_client()
        self._client = client

        output_config: dict[str, Any] = {
            "format": {"type": "json_schema", "schema": dict(request.schema)}
        }
        if request.effort is not None:
            output_config["effort"] = request.effort

        try:
            message = client.messages.create(
                model=request.model,
                max_tokens=request.max_tokens,
                system=request.system,
                messages=[{"role": "user", "content": request.user}],
                output_config=output_config,
            )
        except Exception as error:
            #: Deliberately broad, and re-raised rather than swallowed. The boundary's contract is
            #: that a transport failure becomes a structured result: authentication, rate limits,
            #: connection loss and the SDK's own argument guards are all "no answer arrived", and
            #: they have no single base class that can be named without importing the SDK at module
            #: scope — which is exactly what the lazy import exists to avoid.
            raise LLMError(f"the Anthropic API call failed: {error}") from error

        return LLMResponse(
            text=first_text(message.content),
            stop_reason=message.stop_reason or "",
            usage=usage_of(message.usage),
            model=message.model,
        )


def _build_client() -> Any:
    try:
        import anthropic
    except ImportError as error:  # pragma: no cover — exercised only without the extra installed
        raise LLMError(
            "the anthropic package is not installed; this project's model calls are an optional "
            'extra, installed with `pip install -e ".[llm]"`'
        ) from error
    return anthropic.Anthropic()


def first_text(content: list[Any]) -> str:
    """The first text block of the reply.

    Not `content[0]`: the models think before answering, and a thinking block sits ahead of the
    answer in the list. Indexing blindly would hand `pipeline` an empty string and have it report
    that the model said nothing, on every single document.
    """
    for block in content:
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


def usage_of(usage: Any) -> Usage:
    """The four token counts, with absent cache fields read as zero rather than as unknown."""
    return Usage(
        input_tokens=_count(usage, "input_tokens"),
        output_tokens=_count(usage, "output_tokens"),
        cache_creation_input_tokens=_count(usage, "cache_creation_input_tokens"),
        cache_read_input_tokens=_count(usage, "cache_read_input_tokens"),
    )


def _count(usage: Any, name: str) -> int:
    return int(getattr(usage, name, 0) or 0)
