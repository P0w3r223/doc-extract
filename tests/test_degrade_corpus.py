"""What makes the scanned corpus a paired comparison rather than a second pile of PDFs.

The claims are the foreign corpus's, moved to the other axis:

* **It is paired.** Document by document the gold is M2's gold, and the page is M2's page — printed
  in M2's own layout, by M2's own renderer, before anything happened to it. A difference between a
  run over this corpus and a run over the clean one is therefore the *scanner*.
* **The rung is what the manifest records.** `template` is the axis a report tables by, and this
  corpus varies legibility rather than layout. A manifest naming `classic` here would put the run's
  most informative table under the wrong heading.
* **The layouts still rotate underneath.** If a rung met one layout only, a per-rung drop could
  equally be a per-layout drop and no table could separate them — the same argument M2 makes for
  rotating templates within a tier.
* **The corpus attests to what built it.** A rasterised byte depends on `pypdfium2` and `Pillow`
  the way a printed one depends on the fonts, and a manifest that recorded only the fonts would go
  on matching after an upgrade rewrote every page.
"""

from __future__ import annotations

import json
from collections import Counter

import pytest

from doc_extract.degrade import corpus as degraded
from doc_extract.degrade.rungs import RUNGS, SEARCHABLE
from doc_extract.eval import dataset
from doc_extract.source import document as source_document
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth import render as synth_render
from doc_extract.synth.tiers import BY_NAME as TIERS

#: Two tiers and three documents each, so every rung is met once per tier and the whole thing still
#: renders in seconds. Rasterising is the slow part and it is slow per page, not per document.
SMALL = dict(per_tier=3, tiers=(TIERS["clean"], TIERS["multi_page"]))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    directory = tmp_path_factory.mktemp("scanned")
    degraded.generate(directory, **SMALL)
    return directory


def test_the_gold_is_the_synthetic_corpus_s_gold_document_by_document():
    """The pairing, asserted on the invoice rather than on a count of them."""
    theirs = list(synth_corpus.documents(**SMALL))
    ours = list(degraded.documents(**SMALL))

    assert [document.doc_id for document, _ in ours] == [d.doc_id for d in theirs]
    for (mine, _), yours in zip(ours, theirs, strict=True):
        assert mine.invoice == yours.invoice, mine.doc_id


def test_the_page_a_rung_is_applied_to_is_the_layout_the_synthetic_corpus_assigned():
    """What is varied is legibility, so what is *not* varied has to include the layout."""
    theirs = {document.doc_id: document.template for document in synth_corpus.documents(**SMALL)}

    assert {doc.doc_id: doc.template for doc, _ in degraded.documents(**SMALL)} == theirs


def test_every_rung_meets_every_tier(built):
    entries = list(dataset.load(built).cases)
    by_tier: dict[str, Counter] = {}
    for case in entries:
        by_tier.setdefault(case.tier, Counter())[case.template] += 1

    for tier, counts in by_tier.items():
        assert set(counts) == {rung.name for rung in RUNGS}, tier


def test_the_manifest_records_the_rung_and_not_the_layout(built):
    templates = {case.template for case in dataset.load(built).cases}

    assert templates == {rung.name for rung in RUNGS}
    assert templates.isdisjoint(synth_render.TEMPLATES)


def test_the_underlying_layouts_are_recorded_rather_than_lost(built):
    """They leave the manifest's `template` column, so the provenance block has to carry them."""
    provenance = json.loads((built / synth_corpus.PROVENANCE_NAME).read_text(encoding="utf-8"))
    layouts = provenance["layouts"]

    assert set(layouts.values()) <= set(synth_render.TEMPLATES)
    assert layouts == {
        document.doc_id: document.template for document in synth_corpus.documents(**SMALL)
    }


def test_the_provenance_names_what_a_rasterised_byte_depends_on(built):
    provenance = json.loads((built / synth_corpus.PROVENANCE_NAME).read_text(encoding="utf-8"))

    assert provenance["renderer"] == "scanned"
    assert [rung["name"] for rung in provenance["rungs"]] == [rung.name for rung in RUNGS]
    assert provenance["pypdfium2_version"] not in ("", "unknown")
    assert provenance["pillow_version"] not in ("", "unknown")
    #: Still M2's block underneath: the fonts decide what the page looked like before it was
    #: photographed, and dropping them would make a font swap invisible here alone.
    assert provenance["fonts_sha256"]


def test_the_corpus_verifies_against_its_own_manifest(built):
    """Every page is read back through the hash the manifest attests to, as a run would."""
    corpus = dataset.load(built)

    assert len(corpus.cases) == 6
    for case in corpus.cases:
        case.source()
        case.gold()


def test_a_searchable_page_of_the_corpus_reads_as_its_clean_page_did(built):
    """The control, end to end through the manifest rather than through the renderer alone."""
    printed = {
        document.doc_id: source_document.read(synth_render.render(document).data).text
        for document in synth_corpus.documents(**SMALL)
    }

    for case in dataset.load(built).cases:
        if case.template == SEARCHABLE.name:
            assert case.source().text == printed[case.doc_id], case.doc_id
