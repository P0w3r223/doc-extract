"""The foreign corpus: M2's documents, assigned a foreign layout and written out.

The gold is not regenerated, re-seeded or re-drawn — `synth.corpus.documents()` yields exactly the
invoices the synthetic corpus is built from, and the only thing changed is the `template` each one
carries. So `clean-0000` here and `clean-0000` there are the *same invoice*, and a difference
between two runs is the page.

The manifest, the hashing and the provenance block are M2's, deliberately. They are not
presentation, and a second copy of them would be a second place for a corpus to drift out of the
index that attests to it — the failure the index exists to make impossible. What the block gains is
a `renderer` key, because every `pdf_sha256` under it is a function of this package rather than of
`synth/render.py`, and a run that could not tell which of the two corpora it scored would be a
result nobody could reproduce.

Templates rotate by position within each tier, the same way M2 rotates its three, so every tier
appears in every foreign layout roughly equally often and a per-tier drop is never a per-template
one wearing a tier's name.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from doc_extract.foreign import render as foreign_render
from doc_extract.foreign.dialect import TEMPLATES
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.build import Document
from doc_extract.synth.corpus import Entry
from doc_extract.synth.tiers import TIERS, Tier


def documents(
    *,
    seed: int = synth_corpus.DEFAULT_SEED,
    per_tier: int = synth_corpus.DEFAULT_PER_TIER,
    tiers: tuple[Tier, ...] = TIERS,
    templates: Sequence[str] = TEMPLATES,
) -> Iterator[Document]:
    """M2's documents, each reassigned to a foreign layout. Nothing else about them moves.

    The reassignment is by position **within the tier**, which is how `synth.corpus.documents`
    rotates its own three, so the same tier meets the same layout index in both corpora and the
    pairing holds at the level of the layout as well as of the invoice. Enumerating globally
    coincides with that only while `per_tier` is a multiple of the number of layouts — true at the
    shipping default and false at `--per-tier 5`, which the CLI accepts.
    """
    for index, document in enumerate(
        synth_corpus.documents(seed=seed, per_tier=per_tier, tiers=tiers)
    ):
        yield _with_template(document, templates[index % per_tier % len(templates)])


def _with_template(document: Document, template: str) -> Document:
    return Document(
        doc_id=document.doc_id,
        tier=document.tier,
        template=template,
        seed=document.seed,
        invoice=document.invoice,
        context=document.context,
        overlay=document.overlay,
    )


def generate(
    out_dir: Path,
    *,
    seed: int = synth_corpus.DEFAULT_SEED,
    per_tier: int = synth_corpus.DEFAULT_PER_TIER,
    tiers: tuple[Tier, ...] = TIERS,
    templates: Sequence[str] = TEMPLATES,
    progress: Callable[[Entry], None] | None = None,
) -> list[Entry]:
    """Write the foreign corpus and its manifest, returning the index that was written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[Entry] = []
    for document in documents(seed=seed, per_tier=per_tier, tiers=tiers, templates=templates):
        entry = synth_corpus.write_document(document, out_dir, draw=foreign_render.render)
        entries.append(entry)
        if progress is not None:
            progress(entry)
    synth_corpus.write_index(out_dir, entries, _provenance(
        entries, seed=seed, per_tier=per_tier, tiers=tiers, templates=templates,
    ))
    return entries


def _provenance(
    entries: Sequence[Entry],
    *,
    seed: int,
    per_tier: int,
    tiers: tuple[Tier, ...],
    templates: Sequence[str],
) -> dict[str, Any]:
    """M2's block, plus which renderer drew these bytes.

    Built from `synth.corpus.provenance` rather than assembled here, so the font hashes, the XSD
    hash and the reportlab version — everything a rendered byte silently depends on — are recorded
    by the one function that knows what they are.
    """
    base = asdict(synth_corpus.provenance(
        seed=seed, per_tier=per_tier, tiers=tiers, documents=len(entries),
    ))
    return {**base, "renderer": "foreign", "templates": list(templates)}
