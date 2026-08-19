"""The renderer's fourth input: text a third party put on the page.

The claim M6 rests on is that an injected string reaches the model. It has two halves and both are
asserted here rather than argued: the payload survives **rendering** into the text layer `source/`
reads, in every layout and every placement — and it is not there when nobody put it there.

`invisible` is the case worth a test of its own. White ink on a white page is the version of this
attack that gets past a human, and it is only an attack if pdfplumber still sees it. If a future
reportlab dropped invisible text, the suite's `invisible` column would quietly become a column of
zeroes and read as a defence.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from doc_extract.attack.payloads import BY_NAME
from doc_extract.source import document as source_document
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth import render
from doc_extract.synth.build import Document
from doc_extract.synth.overlay import PLACEMENTS, Overlay
from doc_extract.synth.tiers import BY_NAME as TIERS

PAYLOAD = BY_NAME["total_override"]


def _base(template: str) -> Document:
    """One clean document, printed in the requested layout."""
    document = next(iter(synth_corpus.documents(per_tier=1, tiers=(TIERS["clean"],))))
    return replace(document, template=template)


def _text(document: Document) -> str:
    return source_document.read(render.render(document).data).text


def _squeezed(text: str) -> str:
    return "".join(text.split())


def _with_overlay(document: Document, placement: str, text: str = PAYLOAD.text) -> Document:
    return replace(document, overlay=Overlay(text=text, placement=placement))


@pytest.mark.parametrize("template", render.TEMPLATES)
@pytest.mark.parametrize("placement", PLACEMENTS)
def test_payload_reaches_the_text_layer(template: str, placement: str) -> None:
    """Every placement, in every layout, is readable back out of the PDF."""
    attacked = _with_overlay(_base(template), placement)
    assert _squeezed(PAYLOAD.marker) in _squeezed(_text(attacked))


@pytest.mark.parametrize("template", render.TEMPLATES)
def test_a_clean_page_carries_no_payload(template: str) -> None:
    """The other half: without an overlay the marker is nowhere on the page.

    Without this, a payload whose marker happened to be a word the generator prints anyway would
    make every attack look as though it had reached the model.
    """
    assert _squeezed(PAYLOAD.marker) not in _squeezed(_text(_base(template)))


def test_the_overlay_does_not_touch_the_gold() -> None:
    """An injected instruction does not change what the invoice says — the whole design of M6."""
    document = _base("classic")
    assert _with_overlay(document, "footer").invoice == document.invoice


def test_an_unplaced_overlay_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown placement"):
        Overlay(text="cokolwiek", placement="margin")


def test_an_empty_overlay_is_refused() -> None:
    with pytest.raises(ValueError, match="no text"):
        Overlay(text="   ", placement="footer")


def test_markup_in_a_payload_is_printed_rather_than_parsed() -> None:
    """The fence payload prints `</document>`, which is reportlab's own markup syntax.

    Unescaped it would be swallowed as a tag — the one payload whose entire point is the literal
    characters would arrive on the page with them removed, and the fence would appear to hold for a
    reason that has nothing to do with the fence.
    """
    fence = BY_NAME["fence_break"]
    text = _squeezed(_text(_with_overlay(_base("classic"), "footer", fence.text)))
    assert "</document-0000000000000000>" in text
    assert _squeezed(fence.marker) in text
