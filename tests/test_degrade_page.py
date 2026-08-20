"""What makes a scanned page a measurement rather than a blurred picture.

The rungs are only worth having if each one isolates the thing it claims to:

* **`searchable` changes nothing a text reader can see.** Its whole job is to be the control that
  separates "the image got worse" from "the text layer is gone", and it can only do that if the
  text it yields is the clean corpus's text *exactly*. Anything less and a drop on the other two
  rungs is partly this rung's fault.
* **The other two really have no text layer.** A rung that left a few words behind would report a
  reader as partly working when what it was doing was reading a remnant.
* **The page is still there.** The damage is deliberately mild, and "an illegible page cannot be
  extracted" is not a finding — so every gold value has to remain recoverable from the one rung
  whose text this project can read without a model.
* **The bytes are a function of the seed.** A corpus whose grain was drawn from the ambient random
  state would have a different hash on every build, and its manifest would attest to nothing.
"""

from __future__ import annotations

import random

import pytest
from PIL import Image

from doc_extract.degrade import optics, page
from doc_extract.degrade.rungs import RASTERISED, RUNGS, SCANNED, SEARCHABLE
from doc_extract.ground.resolve import resolve as ground
from doc_extract.source import document as source_document
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth import render as synth_render

#: One document per shape that has ever broken something here: the plain case, the one that runs to
#: two pages, and a correction, whose amounts are negative and whose minus sign is one glyph wide.
SAMPLE = ("clean-0000", "multi_page-0000", "correction-0000")


@pytest.fixture(scope="module")
def built():
    """M2's documents, and the clean page each was printed on, rendered once for the module."""
    documents = {document.doc_id: document for document in synth_corpus.documents()}
    return {
        doc_id: (documents[doc_id], synth_render.render(documents[doc_id]))
        for doc_id in SAMPLE
    }


@pytest.mark.parametrize("doc_id", SAMPLE)
def test_the_searchable_rung_yields_the_clean_corpus_text_exactly(built, doc_id):
    """The control the other two rungs are read against, asserted rather than assumed."""
    document, printed = built[doc_id]
    scanned = page.render(document, SEARCHABLE)

    assert source_document.read(scanned.data).text == source_document.read(printed.data).text


@pytest.mark.parametrize("doc_id", SAMPLE)
@pytest.mark.parametrize("rung", [RASTERISED, SCANNED], ids=lambda rung: rung.name)
def test_a_rung_without_a_text_layer_yields_no_text_at_all(built, doc_id, rung):
    """Not "less text": none. A remnant would be read as a reader partly working."""
    document, _ = built[doc_id]

    assert source_document.read(page.render(document, rung).data).text == ""


@pytest.mark.parametrize("doc_id", SAMPLE)
@pytest.mark.parametrize("rung", RUNGS, ids=lambda rung: rung.name)
def test_the_page_count_survives_the_scanner(built, doc_id, rung):
    document, printed = built[doc_id]

    assert page.render(document, rung).pages == printed.pages


@pytest.mark.parametrize("rung", RUNGS, ids=lambda rung: rung.name)
def test_the_same_document_scans_to_the_same_bytes(built, rung):
    """A corpus that changed on every build could not be checksummed."""
    document, _ = built["clean-0000"]

    assert page.render(document, rung).data == page.render(document, rung).data


def test_every_gold_value_is_still_recoverable_from_a_searchable_page(built):
    """The solvability obligation `foreign/` carries, applied to the axis this package varies.

    Grounded against the page rather than merely compared as strings, because that is the check
    that knows a value can be printed in more than one form — and because grounding is the signal
    M5 built the gate on, so a rung that quietly broke it would go on to break the gate silently.
    """
    unresolved = []
    for doc_id, (document, _) in built.items():
        scanned = source_document.read(page.render(document, SEARCHABLE).data)
        unresolved += [
            f"{doc_id}:{row.field}={row.value}"
            for row in ground(scanned, document.invoice)
            if row.suspicious
        ]

    assert not unresolved, unresolved[:8]


def test_a_harsher_rung_really_is_a_different_picture(built):
    """Three rungs that produced identical pages would be one rung wearing three names."""
    document, _ = built["clean-0000"]

    pages = {rung.name: page.render(document, rung).data for rung in RUNGS}
    assert len(set(pages.values())) == len(RUNGS)
    assert len(pages[SCANNED.name]) < len(pages[RASTERISED.name]), (
        "the harsher rung is coarser and more heavily quantised, so it cannot be the larger file"
    )


# --------------------------------------------------------------------------- the optics alone


def _grey(value: int = 200, size: tuple[int, int] = (40, 30)) -> Image.Image:
    return Image.new(optics.MODE, size, value)


def test_a_step_that_was_asked_for_nothing_is_the_identity():
    """`skew(0)` and `grain(0)` are on the clean rung's path, where they must not touch the page."""
    image = _grey()

    assert optics.skew(image, 0) is image
    assert optics.soften(image, 0) is image
    assert optics.grain(image, random.Random(1), 0) is image


def test_grain_changes_the_page_and_does_so_reproducibly():
    image = _grey()
    once = optics.grain(image, random.Random(7), 0.2)
    again = optics.grain(image, random.Random(7), 0.2)

    assert once.tobytes() != image.tobytes()
    assert once.tobytes() == again.tobytes()


def test_skew_fills_the_exposed_corner_with_paper_rather_than_black():
    """A rotation that filled with black would put a wall of ink where the platen showed through."""
    skewed = optics.skew(_grey(value=0, size=(200, 200)), 5)

    assert skewed.getpixel((0, 0)) == optics.PAPER


def test_requantise_returns_a_jpeg_and_a_worse_one_at_a_lower_quality():
    image = optics.grain(_grey(size=(300, 300)), random.Random(3), 0.4)
    good = optics.requantise(image, 90)
    poor = optics.requantise(image, 30)

    assert good[:2] == b"\xff\xd8", "not a JPEG"
    assert len(poor) < len(good)
