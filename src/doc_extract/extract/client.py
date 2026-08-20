"""The model boundary: one request shape, one response shape, one protocol with one method.

Everything the pipeline needs from a language model is here, and nothing else is. The point of the
narrowness is that `ScriptedClient` is a complete implementation in twenty lines, so M3 — the whole
prompt, schema, parse and repair path — runs offline, deterministically, with no key and no cost.

**A response carries raw text, not a parsed object.** That is a decision about money. Every FA(3)
amount is a `Decimal` compared for exact equality, and the moment a JSON number passes through a
float it stops round-tripping. Holding the model's answer as the string it actually sent leaves the
parse under this project's control — `json.loads(..., parse_float=Decimal)` in `pipeline` — instead
of under an SDK's. `tests/test_extract_pipeline.py` asserts a seventeen-digit amount survives, which
it could not if any float were involved.

**A transport failure is an exception; a model failure is data.** `LLMError` means the request never
produced an answer — no network, no key, a rejected payload. A refusal, a truncation, or a reply
that does not fit the schema is not an error here: it is a `stop_reason` and a body, and `pipeline`
records it as a failure class. Conflating the two would put "the model declined" and "the laptop is
offline" in the same bucket, and M4 reports them separately.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


class LLMError(RuntimeError):
    """The request did not produce an answer. Carries the cause; never raised for a bad answer."""


@dataclass(frozen=True, slots=True)
class Usage:
    """Tokens billed for one attempt, cache included.

    The two cache fields are here because leaving them out would understate cost on exactly the
    workload this project runs — the same system prompt and schema against a hundred documents.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_input_tokens=(
                self.cache_creation_input_tokens + other.cache_creation_input_tokens
            ),
            cache_read_input_tokens=(
                self.cache_read_input_tokens + other.cache_read_input_tokens
            ),
        )


@dataclass(frozen=True, slots=True)
class PageImage:
    """One page of a document, as the bytes of an image and the type they are encoded in.

    M7's scanned corpus has documents with no text layer at all, where the only reader left is one
    that looks at the page. Carried beside `user` rather than encoded into it, because an image is
    a content block of its own on the wire and flattening it into the text would be inventing a
    representation the API does not have.
    """

    media_type: str
    data: bytes


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """One call. Deliberately without a sampling temperature.

    Not an omission: `temperature`, `top_p` and `top_k` are rejected outright by the current Opus
    and Sonnet models, so a field for one would be a field that makes every request fail. Output
    variability is controlled by `effort` and by the prompt, and reproducibility comes from the
    schema and the invariants rather than from a sampler setting that never guaranteed it anyway.

    `images` is empty on every text request, which is what keeps the two paths one code path: a
    client that ignores it answers a vision request exactly as it answers a text one, and the
    scripted model does.
    """

    model: str
    system: str
    user: str
    schema: Mapping[str, object]
    max_tokens: int
    effort: str | None = None
    images: tuple[PageImage, ...] = ()


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """What came back: the body as sent, why generation stopped, and what it cost.

    `model` is the model that actually answered, which is not always the one that was asked — a
    refusal may be served by a fallback. A metric that reported the requested model would be
    reporting the request rather than the result.
    """

    text: str
    stop_reason: str
    usage: Usage
    model: str


class LLMClient(Protocol):
    """One method, so that a fake is as complete an implementation as the real one."""

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Answer a request, or raise `LLMError` if no answer could be obtained."""
        ...
