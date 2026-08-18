"""A model that answers from a script — the whole of M3, offline, with no key and no cost.

Every part of the pipeline except the model itself is deterministic code, and that part is exactly
the part a test cannot pin down. Scripting it makes the rest testable: the prompt, the schema, the
parse, the repair loop and the failure taxonomy all run end to end against replies chosen to
exercise them, including the ones no real model would reliably produce on demand — a refusal, a
truncation, a body that is not JSON.

`oracle` is the interesting one. It replies with the gold document itself, so a passing test says
something stronger than "the pipeline runs": it says a perfect reading of the page survives the
round trip through the wire format and comes back equal to the gold. Anything M4 later scores below
that is the model's, not the plumbing's — which is why the same function becomes baseline B0.

**The scripted usage is zero unless a test sets it.** A fake that invented plausible token counts
would put fabricated numbers exactly where a cost metric reads, and this project does not report
metrics that are hardcoded values.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field

from doc_extract.extract import wire
from doc_extract.extract.client import LLMError, LLMRequest, LLMResponse, Usage
from doc_extract.schema.ksef import Invoice

SCRIPTED_MODEL = "scripted"


@dataclass(frozen=True, slots=True)
class Reply:
    """One canned answer, in the same shape a real client returns."""

    text: str
    stop_reason: str = "end_turn"
    usage: Usage = field(default_factory=Usage)
    model: str = SCRIPTED_MODEL


class ScriptedClient:
    """Answers requests from a list, in order, recording what it was asked.

    An `LLMError` in the script is raised rather than returned, which is how a transport failure is
    exercised. Running out of replies raises one too: a pipeline that called the model more often
    than the test expected has changed its stage order, and that should fail loudly.
    """

    def __init__(self, *replies: Reply | LLMError) -> None:
        self._replies: list[Reply | LLMError] = list(replies)
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if not self._replies:
            raise LLMError(
                f"the script is exhausted after {len(self.requests)} request(s); the pipeline "
                "called the model more often than the script expects"
            )
        reply = self._replies.pop(0)
        if isinstance(reply, LLMError):
            raise reply
        return LLMResponse(
            text=reply.text, stop_reason=reply.stop_reason, usage=reply.usage, model=reply.model
        )

    @property
    def remaining(self) -> int:
        return len(self._replies)


def as_reply(invoice: Invoice) -> Reply:
    """The gold, serialised into the wire shape, as a reply.

    `ensure_ascii=False` because the fields carry Polish diacritics and an escaped body would be a
    different string from the one a real model sends — the prompt and the parse should be exercised
    on the bytes that actually occur. A test wanting a variation takes one of these through
    `dataclasses.replace`.
    """
    return Reply(text=json.dumps(wire.serialise(invoice), ensure_ascii=False))


def oracle(invoice: Invoice, *, replies: int = 1) -> ScriptedClient:
    """A model that reads the page perfectly — the upper bound M4 measures everything against."""
    return ScriptedClient(*(as_reply(invoice) for _ in range(replies)))


def script(replies: Iterable[Reply | LLMError]) -> ScriptedClient:
    """A client from an iterable, for tests that build their replies in a comprehension."""
    return ScriptedClient(*replies)
