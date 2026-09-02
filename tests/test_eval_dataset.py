"""What a manifest is allowed to leave out, and what the corpus infers when it does.

Every corpus this project has scored so far was written by `synth/corpus.py`, so every manifest
carried the same columns and nothing here had to decide what a missing one meant. A held-out set of
documents nobody generated has no seed and no tier, and inventing values for both is how a real
corpus starts lying about itself. These are the cases that arise the first time a manifest is
written by hand.

The other half of the contract is asserted where it belongs: `tests/test_results_committed.py`
re-renders all 24 committed reports, so *reading two axes as facets must render the two tables it
always did*, byte for byte. That check is the reason this generalisation could be made at all, and
it is why nothing here asserts the shape of a `report.md`.
"""

from __future__ import annotations

import json
import zlib
from pathlib import Path

import pytest

from doc_extract.eval import dataset


def _manifest(tmp_path: Path, *rows: dict) -> Path:
    (tmp_path / dataset.MANIFEST_NAME).write_text(
        "\n".join(json.dumps(row) for row in rows), encoding="utf-8"
    )
    return tmp_path


def _row(doc_id: str = "d-0000", **over) -> dict:
    row = {
        "doc_id": doc_id,
        "tier": "clean",
        "template": "classic",
        "seed": 7,
        "xml": f"{doc_id}.xml",
        "pdf": f"{doc_id}.pdf",
        "xml_sha256": "a" * 64,
        "pdf_sha256": "b" * 64,
        "pages": 1,
    }
    row.update(over)
    return row


def test_a_generated_manifest_is_read_as_the_two_axes_it_varies(tmp_path):
    """`tier` and `template` are not special to this layer — they are what a generated corpus
    happens to declare, and the inference keeps the 24 committed runs readable unchanged."""
    corpus = dataset.load(_manifest(tmp_path, _row()))
    case = corpus.cases[0]

    assert case.facets == (("tier", "clean"), ("template", "classic"))
    assert case.tier == "clean"
    assert case.template == "classic"


def test_a_manifest_may_name_its_own_axes(tmp_path):
    """The held-out case: a corpus that varies issuer and legibility, and neither of the two names
    this project's generator happens to use."""
    corpus = dataset.load(_manifest(tmp_path, _row(
        facets={"issuer": "comarch", "legibility": "born-digital"},
    )))
    case = corpus.cases[0]

    assert case.facets == (("issuer", "comarch"), ("legibility", "born-digital"))
    assert case.facet("issuer") == "comarch"
    assert case.tier == "", "a corpus with no difficulty band must not invent one"


def test_an_axis_this_corpus_does_not_vary_is_empty_rather_than_missing(tmp_path):
    """`facet` answers for every name, so a caller never has to know which corpus it is reading."""
    case = dataset.load(_manifest(tmp_path, _row())).cases[0]
    assert case.facet("issuer") == ""


def test_a_document_nobody_generated_gets_a_seed_derived_from_its_name(tmp_path):
    """Every baseline takes a seed — `noisy` and `corrupt` are only reproducible with one — and a
    real document has none. Deriving it keeps every baseline runnable on every corpus, which is
    this project's rule that a baseline with its own code path measures its own code path.

    Asserted against `zlib.crc32` directly rather than against a recorded constant: the claim is
    *derived from the document's name*, and a golden number would still pass if the derivation
    started reading something else.
    """
    row = _row("faktura-2026-03-17")
    del row["seed"]
    case = dataset.load(_manifest(tmp_path, row)).cases[0]

    assert case.seed == zlib.crc32(b"faktura-2026-03-17")


def test_a_recorded_seed_is_preferred_over_a_derived_one(tmp_path):
    """The generated corpora must keep the seed that produced them, or a run stops being the run
    it names."""
    assert dataset.load(_manifest(tmp_path, _row(seed=1234))).cases[0].seed == 1234


def test_a_corpus_with_no_manifest_says_how_to_build_one(tmp_path):
    with pytest.raises(dataset.CorpusError, match="no manifest"):
        dataset.load(tmp_path)


def test_an_empty_manifest_is_refused_rather_than_scored_as_a_complete_run(tmp_path):
    """Nothing scored over nothing is 100 % of nothing, and coverage would agree with it."""
    with pytest.raises(dataset.CorpusError, match="describes no documents"):
        dataset.load(_manifest(tmp_path))
