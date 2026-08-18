"""The corpus is a function of one integer, and the manifest is what makes that checkable.

Nothing here is committed, so reproducibility replaces version control: the seed in the manifest
has to be enough to rebuild the identical bytes. These tests pin the two properties that guarantee
it — the same seed gives the same corpus, and a document's identity does not depend on how many
other documents were generated alongside it.
"""

from __future__ import annotations

import json

from doc_extract.synth import corpus
from doc_extract.synth.render import TEMPLATES
from doc_extract.synth.tiers import BY_NAME, TIERS


def _small(names=("clean", "correction")):
    return tuple(BY_NAME[name] for name in names)


def test_the_manifest_describes_every_file_it_wrote(tmp_path):
    entries = corpus.generate(tmp_path, per_tier=2, tiers=_small())
    rows = [json.loads(line) for line in
            (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]

    assert len(rows) == len(entries) == 4
    for row in rows:
        assert (tmp_path / row["xml"]).exists()
        assert (tmp_path / row["pdf"]).exists()


def test_the_recorded_hashes_match_the_files_on_disk(tmp_path):
    """A manifest whose hashes drifted would be worse than no manifest at all."""
    import hashlib

    for entry in corpus.generate(tmp_path, per_tier=2, tiers=_small()):
        xml_bytes = (tmp_path / entry.xml).read_bytes()
        pdf_bytes = (tmp_path / entry.pdf).read_bytes()
        assert hashlib.sha256(xml_bytes).hexdigest() == entry.xml_sha256
        assert hashlib.sha256(pdf_bytes).hexdigest() == entry.pdf_sha256


def test_the_same_seed_rebuilds_the_identical_corpus(tmp_path):
    first = corpus.generate(tmp_path / "a", per_tier=2, tiers=_small())
    second = corpus.generate(tmp_path / "b", per_tier=2, tiers=_small())
    assert [entry.pdf_sha256 for entry in first] == [entry.pdf_sha256 for entry in second]
    assert [entry.xml_sha256 for entry in first] == [entry.xml_sha256 for entry in second]


def test_a_different_seed_rebuilds_a_different_corpus(tmp_path):
    first = corpus.generate(tmp_path / "a", seed=1, per_tier=2, tiers=_small())
    second = corpus.generate(tmp_path / "b", seed=2, per_tier=2, tiers=_small())
    assert [entry.xml_sha256 for entry in first] != [entry.xml_sha256 for entry in second]


def test_a_document_does_not_change_when_the_corpus_around_it_grows():
    """Seeds are derived from the document's own name, so adding a tier disturbs nothing else.

    Without this, generating one more document per tier would shift every subsequent draw, and two
    runs of the generator could not be compared — only rerun.
    """
    few = {doc.doc_id: doc.invoice for doc in corpus.documents(per_tier=2, tiers=_small())}
    many = {doc.doc_id: doc.invoice for doc in corpus.documents(per_tier=5, tiers=TIERS)}
    shared = set(few) & set(many)
    assert shared
    assert all(few[doc_id] == many[doc_id] for doc_id in shared)


def test_templates_rotate_within_each_tier():
    """Otherwise a per-tier accuracy drop could equally be a per-template one, and no table could
    tell them apart."""
    seen: dict[str, set[str]] = {}
    for document in corpus.documents(per_tier=len(TEMPLATES)):
        seen.setdefault(document.tier, set()).add(document.template)
    assert all(templates == set(TEMPLATES) for templates in seen.values())


def test_every_tier_is_represented():
    tiers = {document.tier for document in corpus.documents(per_tier=1)}
    assert tiers == {tier.name for tier in TIERS}


def test_the_manifest_records_the_seed_each_document_was_built_from(tmp_path):
    for entry in corpus.generate(tmp_path, per_tier=1, tiers=_small()):
        assert entry.seed > 0
        assert entry.doc_id.startswith(entry.tier)


def test_the_manifest_records_what_the_corpus_was_built_from(tmp_path):
    """Two runs whose hashes differ must be tellable apart from a `pip install -U` in between.

    Every `pdf_sha256` is a function of the reportlab version and the vendored fonts, and every
    document is a function of the seed and the tier set. Recording only the outputs would leave a
    changed hash unexplainable, which is the one thing a provenance file exists to prevent.
    """
    corpus.generate(tmp_path, per_tier=2, tiers=_small())
    meta = json.loads((tmp_path / corpus.PROVENANCE_NAME).read_text(encoding="utf-8"))

    assert meta["corpus_seed"] == corpus.DEFAULT_SEED
    assert meta["per_tier"] == 2
    assert meta["tiers"] == ["clean", "correction"]
    assert meta["documents"] == 4
    assert meta["reportlab_version"][0].isdigit()
    assert len(meta["fa3_xsd_sha256"]) == 64
    assert set(meta["fonts_sha256"]) == {"DejaVuSans", "DejaVuSans-Bold"}


def test_the_recorded_font_hashes_are_the_vendored_ones(tmp_path):
    """The manifest must name the fonts actually used, not a digest copied from a document."""
    import hashlib

    from doc_extract.synth import render

    corpus.generate(tmp_path, per_tier=1, tiers=_small(("clean",)))
    meta = json.loads((tmp_path / corpus.PROVENANCE_NAME).read_text(encoding="utf-8"))
    for name, recorded in meta["fonts_sha256"].items():
        on_disk = hashlib.sha256((render.FONT_DIR / f"{name}.ttf").read_bytes()).hexdigest()
        assert recorded == on_disk


def test_regenerating_smaller_leaves_no_file_the_manifest_does_not_describe(tmp_path):
    """A leftover PDF is a corpus larger than the manifest attests to, and nothing would notice."""
    corpus.generate(tmp_path, per_tier=3, tiers=_small())
    corpus.generate(tmp_path, per_tier=1, tiers=_small(("clean",)))

    rows = [json.loads(line) for line in
            (tmp_path / corpus.MANIFEST_NAME).read_text(encoding="utf-8").splitlines()]
    described = {row["xml"] for row in rows} | {row["pdf"] for row in rows}
    described |= {corpus.MANIFEST_NAME, corpus.PROVENANCE_NAME}
    assert {path.name for path in tmp_path.iterdir()} == described
