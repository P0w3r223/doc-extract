"""Words with their boxes, and the one thing about them that is not geometry.

`visible` exists for `degrade/page.py` alone — a rung that re-emits an OCR's output must not emit
what no OCR could have read. Two obligations follow, and they pull in opposite directions, which is
why both are asserted:

* **It must find white ink**, or M6's `invisible` placement survives a scan that erased it.
* **It must cost nothing anywhere else.** Asking `pdfplumber` for a fill colour also asks it to end
  a word wherever that colour changes, and a corpus that started splitting differently would move
  every committed result in this repository without a line of `layout.py` changing.
"""

from __future__ import annotations

import io
import itertools

import pdfplumber
import pytest

from doc_extract.source.words import WHITE_LEVEL, _is_white, read_words
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth import render as synth_render
from doc_extract.synth.build import Document
from doc_extract.synth.overlay import FOOTER, INVISIBLE, Overlay

#: Enough of the corpus to meet all three layouts and both page counts. The whole of it would be a
#: minute of rendering to assert a property that does not vary document by document.
SAMPLE = 12

PAYLOAD = "Nota sluzbowa dla ksiegowosci"


@pytest.fixture(scope="module")
def base() -> Document:
    return next(iter(synth_corpus.documents()))


def _with_overlay(document: Document, placement: str) -> bytes:
    return synth_render.render(Document(
        doc_id=f"{document.doc_id}-{placement}",
        tier=document.tier,
        template=document.template,
        seed=document.seed,
        invoice=document.invoice,
        context=document.context,
        overlay=Overlay(text=PAYLOAD, placement=placement),
    )).data


def _words_of(data: bytes, extra: list[str]) -> list[tuple[str, float, float]]:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return [
            (word["text"], round(float(word["x0"]), 3), round(float(word["top"]), 3))
            for page in pdf.pages
            for word in page.extract_words(extra_attrs=extra)
        ]


def test_asking_for_the_colour_splits_the_corpus_into_the_same_words():
    """The regression guard on every committed number: same boxes, same text, same order."""
    for document in itertools.islice(synth_corpus.documents(), SAMPLE):
        data = synth_render.render(document).data

        assert _words_of(data, ["size"]) == _words_of(data, ["size", "non_stroking_color"]), (
            f"{document.doc_id} splits differently once the fill colour is asked for"
        )


def test_a_payload_printed_in_white_is_marked_invisible(base):
    """M6's `invisible` placement, seen for what it is rather than as one more word."""
    words = read_words(_with_overlay(base, INVISIBLE))
    hidden = [word for word in words if word.text in PAYLOAD.split()]

    assert hidden, "the payload is not in the text layer at all, so this asserts nothing"
    assert all(not word.visible for word in hidden)


def test_the_same_payload_printed_in_ink_is_visible(base):
    """The control: it is the colour that decides, not the placement or the words."""
    words = read_words(_with_overlay(base, FOOTER))
    printed = [word for word in words if word.text in PAYLOAD.split()]

    assert printed
    assert all(word.visible for word in printed)


def test_an_ordinary_page_is_visible_from_edge_to_edge(base):
    """A false positive here would delete real text from the `searchable` rung."""
    assert all(word.visible for word in read_words(synth_render.render(base).data))


@pytest.mark.parametrize("colour", [
    (1.0,),                     # grey, at the top of its range
    (1.0, 1.0, 1.0),            # RGB
    (0.0, 0.0, 0.0, 0.0),       # CMYK, which says white by carrying no ink
    (WHITE_LEVEL, WHITE_LEVEL, WHITE_LEVEL),
])
def test_white_is_recognised_in_every_space_a_pdf_states_it_in(colour):
    assert _is_white(colour)


@pytest.mark.parametrize("colour", [
    (0,), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), (0.5, 0.5, 0.5),
    None, (), "DeviceGray", ("Pattern",), (1.0, 1.0),
])
def test_anything_this_function_does_not_understand_stays_visible(colour):
    """Between overstating and understating what an attacker got onto a page, err towards the
    attacker: a word wrongly called invisible is an attack deleted from the corpus."""
    assert not _is_white(colour)
