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
from doc_extract.eval import dataset, run
from doc_extract.eval.baselines import BY_NAME as BASELINES
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


# --------------------------------------------------------------- what the gate can say about a scan


def test_a_perfect_reading_of_a_scan_raises_no_alarm_and_is_measured_only_where_it_could_be(built):
    """M7c's finding at its source, and the correction to it, on the corpus that produced both.

    `oracle` reads every document exactly right. Before grounding could say *there was nothing to
    look in*, the two text-less rungs answered `UNGROUNDED` for every asserted value and the run
    drew 3989 false alarms on a reading with nothing wrong in it — inverting rather than degrading,
    because an ungrounded correct value looks exactly like an ungrounded fabricated one.

    Now those values leave the curve instead. Two claims, and the second is what keeps the first
    from being satisfiable by measuring nothing: no alarm anywhere, **and** the survivors are
    exactly the rung that kept a text layer.
    """
    corpus = dataset.load(built)
    records = run.predict(corpus, BASELINES["oracle"])
    curve = run.gate(corpus, records)

    assert curve.wrong == 0, "the premise: a perfect reading"
    assert all(signal.false_positive == 0 for signal in curve.signals)
    assert curve.without_text > 0, "two of the three rungs carry no text layer"

    searchable = {case.doc_id for case in corpus.cases if case.template == SEARCHABLE.name}
    assert {row.doc_id for row in curve.judged} == searchable
    assert curve.points[0].coverage == 1.0, "and on that rung the reading grounds completely"
