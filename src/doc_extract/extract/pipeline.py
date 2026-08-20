"""Source document to `Invoice`, in a fixed order, with a repair loop this project owns.

The order never varies and never branches on what the document says: seal the text, ask once, parse,
and — only if the answer failed *this* project's validator — ask again with that validator's errors.
A stage order that depended on the content of an untrusted document would be a stage order the
document could choose.

**The repair is owned rather than delegated.** A schema retry that simply re-sent the request would
be a second sample; this one carries the specific field paths `Invoice` rejected, so the second
attempt is answering a question. It is bounded (`max_repairs`), it has its **own** token budget, and
every attempt is recorded — a repair that succeeds still leaves the failed attempt in the record,
with its tokens, because the cost of an extraction is the cost of getting to it.

**Money never touches a float.** The model's answer is parsed from the raw body with
`parse_float=Decimal`, so a JSON number arrives as the exact decimal that was written rather than
the nearest double. The wire format asks for strings anyway, which makes this belt and braces — but
the braces are cheap and `tests/test_extract_pipeline.py` proves the belt by sending seventeen
significant digits through and requiring them back unchanged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from doc_extract.extract import prompt, wire
from doc_extract.extract.client import (
    LLMClient,
    LLMError,
    LLMRequest,
    LLMResponse,
    PageImage,
    Usage,
)
from doc_extract.extract.result import REPAIRABLE, Attempt, Extraction, FailureClass, Stage
from doc_extract.schema.ksef import Invoice
from doc_extract.source.document import SourceDocument

#: The model asked unless a caller says otherwise. Named here rather than passed everywhere so that
#: a result file can record which default produced it; M4 varies it and reports per model.
DEFAULT_MODEL = "claude-opus-5"

#: Extraction and repair carry separate budgets, so "ran out of tokens" can be attributed to a
#: stage. Both are generous because current models think before answering and `max_tokens` bounds
#: the thinking and the answer together — a budget sized to the JSON alone truncates mid-object and
#: charges the loss to the extractor. The sizing is not a guess: the corpus's `multi_page` tier
#: prints 26 to 34 rows, and one row is eight fields, so the answer alone runs to several thousand
#: tokens before a single token of reasoning. 16000 also keeps a non-streaming request inside the
#: SDK's HTTP timeout, which a larger ceiling would not.
EXTRACTION_MAX_TOKENS = 16000
REPAIR_MAX_TOKENS = 8192

#: How many validator errors travel back to the model. A malformed answer can produce one error per
#: line item; the cap keeps a repair prompt from being mostly complaint, and the errors are ordered
#: by field path so the ones that are cut are not systematically the same fields.
MAX_REPORTED_ERRORS = 20

#: `stop_reason` values that decide the outcome before the body is even read. Public because a
#: caller that needs to *produce* one — M6's compliant control answers a denial payload with a
#: refusal — must use the same literal this function compares against, and two private copies of a
#: protocol string are two things that can drift while every test still passes.
REFUSAL = "refusal"
TRUNCATED = "max_tokens"


@dataclass(frozen=True, slots=True)
class ExtractionConfig:
    """Everything about a run that a caller may vary, and nothing about a document."""

    model: str = DEFAULT_MODEL
    max_tokens: int = EXTRACTION_MAX_TOKENS
    repair_max_tokens: int = REPAIR_MAX_TOKENS
    max_repairs: int = 1
    #: Reasoning effort, passed through when set. `None` leaves the API's own default in place
    #: rather than pinning a value this project has not measured.
    effort: str | None = None


DEFAULT_CONFIG = ExtractionConfig()


def extract(
    document: SourceDocument,
    client: LLMClient,
    *,
    config: ExtractionConfig = DEFAULT_CONFIG,
    images: tuple[PageImage, ...] = (),
) -> Extraction:
    """One document, at most `1 + max_repairs` calls, always a result and never an exception.

    `images` chooses the modality and nothing else. Supplied, the request carries the pages and the
    system prompt for reading them; left out, it carries the sealed text exactly as before. The
    stage order, the repair budget, the failure taxonomy and the usage accounting are one code path
    for both — a vision arm that ran through a pipeline of its own would report a failure taxonomy
    that could not be compared with the text arm's, which is the whole of what M7d is for.

    `document` is still the source of the *text* turn, and on a scanned page it is empty. That is
    not a special case to guard: a scanned document read as text is a document with nothing in it,
    and the pipeline reports what that produces rather than refusing to try.
    """
    schema = wire.invoice_schema()
    attempts: list[Attempt] = []
    vision = bool(images)
    message = prompt.vision_message(len(images)) if vision else prompt.extraction_message(document)
    stage = Stage.EXTRACT
    max_tokens = config.max_tokens

    for _ in range(config.max_repairs + 1):
        request = LLMRequest(
            model=config.model,
            system=prompt.SYSTEM_VISION if vision else prompt.SYSTEM,
            user=message,
            schema=schema,
            max_tokens=max_tokens,
            effort=config.effort,
            images=images,
        )
        try:
            response = client.complete(request)
        except LLMError as error:
            attempts.append(_client_error(stage, config.model, error))
            return Extraction(invoice=None, attempts=tuple(attempts))

        invoice, failure, detail = read(response)
        attempts.append(Attempt(
            stage=stage,
            model=response.model,
            stop_reason=response.stop_reason,
            usage=response.usage,
            failure=failure,
            detail=detail,
        ))
        if invoice is not None:
            return Extraction(invoice=invoice, attempts=tuple(attempts))
        if failure not in REPAIRABLE:
            break

        message = (
            prompt.vision_repair_message(previous=response.text, errors=detail)
            if vision
            else prompt.repair_message(document, previous=response.text, errors=detail)
        )
        stage = Stage.REPAIR
        max_tokens = config.repair_max_tokens

    return Extraction(invoice=None, attempts=tuple(attempts))


def read(response: LLMResponse) -> tuple[Invoice | None, FailureClass, str]:
    """One response to an invoice, or to the named reason there isn't one.

    `stop_reason` is consulted before the body, and that order matters. A refused or truncated reply
    can still carry text — a partial object, or a sentence explaining the refusal — and parsing it
    first would report a JSON error where the real finding is that the model declined or ran out of
    room. The failure class has to name what actually happened, because M4 counts these.
    """
    if response.stop_reason == REFUSAL:
        return None, FailureClass.REFUSED, "the model declined the request"
    if response.stop_reason == TRUNCATED:
        return None, FailureClass.TRUNCATED, (
            "generation stopped at the token ceiling, so the body is a prefix of an answer"
        )
    if not response.text.strip():
        return None, FailureClass.EMPTY, "the model stopped without answering"

    try:
        payload = json.loads(response.text, parse_float=Decimal)
    except json.JSONDecodeError as error:
        return None, FailureClass.MALFORMED_JSON, f"the body is not JSON: {error}"
    if not isinstance(payload, dict):
        return None, FailureClass.MALFORMED_JSON, (
            f"the body is a JSON {type(payload).__name__}, and the schema asks for an object"
        )

    try:
        return Invoice.model_validate(payload), FailureClass.NONE, ""
    except ValidationError as error:
        return None, FailureClass.SCHEMA_INVALID, describe(error)


def describe(error: ValidationError) -> str:
    """Pydantic's complaint as field paths a model can act on, without its internal formatting."""
    lines = [
        f"{_path(issue['loc'])}: {issue['msg']}"
        for issue in sorted(error.errors(), key=lambda issue: _path(issue["loc"]))
    ]
    dropped = len(lines) - MAX_REPORTED_ERRORS
    if dropped > 0:
        lines = [*lines[:MAX_REPORTED_ERRORS], f"... and {dropped} more"]
    return "\n".join(lines)


def _path(location: tuple[Any, ...]) -> str:
    return ".".join(str(part) for part in location) or "(root)"


def _client_error(stage: Stage, model: str, error: LLMError) -> Attempt:
    return Attempt(
        stage=stage,
        model=model,
        stop_reason="",
        usage=Usage(),
        failure=FailureClass.CLIENT_ERROR,
        detail=str(error),
    )
