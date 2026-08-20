"""The image path, and the one property that makes a text↔image gap a measurement.

A model reading a scan is a second arm of the same study, and a second arm is only comparable while
everything except the modality is held: the same schema, the same repair loop with the same budget,
the same failure taxonomy, the same usage accounting — and the same prompt everywhere the prompt is
not *about* the modality. So the assertions here are mostly about what did **not** change.

The one thing that is genuinely different is the trust boundary. The text path seals the document in
a marker derived from its own bytes; an image has no such handle and the separation is structural
instead — the page is a content block of its own and can never occupy the turn's instruction slot.
That is asserted here rather than described, because it is the property `docs/adr/0001` claims.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any

import pytest

from doc_extract.degrade import corpus as degraded
from doc_extract.degrade.rungs import RASTERISED
from doc_extract.eval import dataset
from doc_extract.extract import pipeline, prompt
from doc_extract.extract.anthropic_client import AnthropicClient
from doc_extract.extract.client import LLMRequest, LLMResponse, PageImage, Usage
from doc_extract.extract.wire import serialise
from doc_extract.source import document as source_document
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.tiers import BY_NAME as TIERS

PAGES = (PageImage(media_type="image/png", data=b"\x89PNG-one"),
         PageImage(media_type="image/png", data=b"\x89PNG-two"))


class _Recorder:
    """An `LLMClient` that answers from a script and keeps every request it was given."""

    def __init__(self, *replies: str) -> None:
        self._replies = list(replies)
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        text = self._replies.pop(0) if len(self._replies) > 1 else self._replies[0]
        return LLMResponse(text=text, stop_reason="end_turn", usage=Usage(), model="fake")


@pytest.fixture(scope="module")
def document():
    """A page with no text on it — which is what a scanned document actually is.

    Built rather than parsed, and empty on purpose: the image path must not be reading it, and a
    fixture carrying text would let a request that quietly fell back to the text turn still pass.
    """
    return source_document.SourceDocument(text="", words=(), cells=(), pages=1)


# --------------------------------------------------------------------------- the two prompts


def test_the_two_system_prompts_share_their_blocks_rather_than_merely_resembling_them():
    """A gap measured across two independently written prompts is partly a gap between prompts."""
    for block in prompt.SHARED_BLOCKS:
        assert block in prompt.SYSTEM
        assert block in prompt.SYSTEM_VISION


def test_the_image_prompt_promises_no_fence_and_the_text_prompt_still_does():
    """The difference is real and is not hidden: only one of the two can name a delimiter."""
    assert "<document-" in prompt.SYSTEM
    assert "<document-" not in prompt.SYSTEM_VISION
    assert "image" in prompt.SYSTEM_VISION.casefold()


def test_the_image_prompt_still_forbids_computing_a_value():
    """The single most load-bearing instruction in the file, and the detector depends on it."""
    assert "Transcribe, never compute." in prompt.SYSTEM_VISION


def test_the_image_prompt_names_no_label_this_corpus_happens_to_print():
    """The rule `test_extract_prompt.py` holds `SYSTEM` to, applied to the prompt beside it."""
    fitted = ("Numer faktury", "Do zapłaty", "Sprzedawca", "Nabywca", "Razem", "Adnotacje")

    assert not [label for label in fitted if label in prompt.SYSTEM_VISION]


# --------------------------------------------------------------------------- the pipeline


def test_images_choose_the_modality_and_travel_with_the_request(document):
    client = _Recorder(json.dumps(serialise(_gold())))
    pipeline.extract(document, client, images=PAGES)

    (request,) = client.requests
    assert request.images == PAGES
    assert request.system == prompt.SYSTEM_VISION
    assert "2 page image(s)" in request.user


def test_without_images_nothing_about_the_text_path_moves(document):
    client = _Recorder(json.dumps(serialise(_gold())))
    pipeline.extract(document, client)

    (request,) = client.requests
    assert request.images == ()
    assert request.system == prompt.SYSTEM


def test_a_repair_re_sends_the_pages_rather_than_working_from_the_previous_answer(document):
    """A repair with only the model's own transcription would be correcting it against itself."""
    client = _Recorder('{"kind": "VAT"}', json.dumps(serialise(_gold())))
    result = pipeline.extract(document, client, images=PAGES)

    first, second = client.requests
    assert result.invoice is not None
    assert second.images == PAGES == first.images
    assert second.system == prompt.SYSTEM_VISION
    assert "previous answer" in second.user


def test_a_repair_seals_the_previous_answer_on_the_image_path_too(document):
    """An answer read off an attacked page carries that page's text; re-sending it bare would give
    the injection a second and more trusted position in the prompt."""
    client = _Recorder('{"kind": "VAT"}', json.dumps(serialise(_gold())))
    pipeline.extract(document, client, images=PAGES)

    _, repair = client.requests
    assert "<previous-answer-" in repair.user


def test_the_failure_taxonomy_is_the_same_one_on_both_paths(document):
    """The point of one pipeline: a vision arm's failure classes compare with a text arm's."""
    text = pipeline.extract(document, _Recorder("not json"))
    vision = pipeline.extract(document, _Recorder("not json"), images=PAGES)

    assert vision.failure == text.failure
    assert [attempt.stage for attempt in vision.attempts] == [a.stage for a in text.attempts]


# --------------------------------------------------------------------------- the wire


def test_the_pages_are_sent_as_image_blocks_after_the_instruction():
    """The turn says what is arriving before it arrives, which is the order the trust rule is
    written for — and the pixels are never in the block the instructions are in."""
    sdk = _SDK()
    AnthropicClient(sdk).complete(_request(images=PAGES))

    content = sdk.messages.calls[0]["messages"][0]["content"]
    assert [block["type"] for block in content] == ["text", "image", "image"]
    assert content[0]["text"] == "USER"
    assert content[1]["source"] == {
        "type": "base64", "media_type": "image/png",
        "data": base64.b64encode(PAGES[0].data).decode("ascii"),
    }


def test_a_request_with_no_image_is_the_string_it_always_was():
    """The text path's bytes on the wire do not move because a second path was added beside it."""
    sdk = _SDK()
    AnthropicClient(sdk).complete(_request())

    assert sdk.messages.calls[0]["messages"] == [{"role": "user", "content": "USER"}]


# --------------------------------------------------------------------------- the corpus


def test_a_case_hands_over_one_image_per_page_of_the_document_it_verified(tmp_path):
    """Rasterised from the same verified bytes `source()` reads, so both arms see one document."""
    directory = tmp_path / "scanned"
    degraded.generate(
        directory, per_tier=1, tiers=(TIERS["clean"], TIERS["multi_page"]), rungs=(RASTERISED,)
    )
    cases = {case.doc_id: case for case in dataset.load(directory).cases}

    for doc_id, case in cases.items():
        images = case.images()
        assert len(images) == case.pages, doc_id
        assert {image.media_type for image in images} == {"image/png"}
        assert all(image.data[:8] == b"\x89PNG\r\n\x1a\n" for image in images), doc_id


def _gold():
    return next(iter(synth_corpus.documents(per_tier=1, tiers=(TIERS["clean"],)))).invoice


def _request(**over: Any) -> LLMRequest:
    return LLMRequest(
        model="claude-opus-5", system="SYSTEM", user="USER",
        schema={"type": "object"}, max_tokens=16000, **over,
    )


@dataclass
class _Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class _Block:
    type: str
    text: str = "{}"


@dataclass
class _Message:
    content: list[_Block] = field(default_factory=lambda: [_Block("text")])
    stop_reason: str | None = "end_turn"
    usage: _Usage = field(default_factory=_Usage)
    model: str = "claude-opus-5"


class _Messages:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _Message:
        self.calls.append(kwargs)
        return _Message()


class _SDK:
    def __init__(self) -> None:
        self.messages = _Messages()
