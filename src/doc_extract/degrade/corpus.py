"""The scanned corpus: M2's documents, put through a scanner and written out.

The gold is not regenerated, re-seeded or re-drawn. `synth.corpus.documents()` yields exactly the
invoices the synthetic corpus is built from, M2's own renderer prints them in M2's own layout, and
the only thing that happens afterwards is that the page becomes a picture of itself. So `clean-0000`
here and `clean-0000` there are the same invoice printed the same way, and a difference between two
runs is the **legibility of the page** — the third and last thing M7 varies one at a time.

**A document's `template` is the rung, not the layout it was printed in.** The manifest has one
column for what a page looks like and the whole point of this corpus is which scanner it went
through, so that is what goes in it and what `report.by_template` therefore reports. The underlying
layout still rotates the way M2 rotates it — every rung meets every layout roughly equally often —
which is exactly what stops a per-rung drop from being a per-layout drop wearing a rung's name. The
rotation itself is recorded in the provenance block rather than per row.

The manifest, the hashing and the provenance block are M2's, for the reason `foreign/corpus.py`
gives: a second copy of them is a second place for a corpus to drift out of the index that attests
to it. What the block gains is `renderer`, the rungs, and the versions of the two libraries that
decide what a rasterised byte is — a `pip install -U` of either rewrites every `pdf_sha256` here the
way a substituted font rewrites M2's.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import asdict
from importlib import metadata
from pathlib import Path
from typing import Any

from doc_extract.degrade import page as scanner
from doc_extract.degrade.rungs import RUNGS, Rung
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.build import Document
from doc_extract.synth.corpus import Entry
from doc_extract.synth.tiers import TIERS, Tier


def documents(
    *,
    seed: int = synth_corpus.DEFAULT_SEED,
    per_tier: int = synth_corpus.DEFAULT_PER_TIER,
    tiers: tuple[Tier, ...] = TIERS,
    rungs: Sequence[Rung] = RUNGS,
) -> Iterator[tuple[Document, Rung]]:
    """M2's documents, each paired with the scanner its page is put through.

    The document is yielded **unchanged**, still carrying the layout it was printed in, because that
    is what has to be drawn. Which rung it met is the second element rather than a field on it: the
    manifest's view of the document — where `template` is the rung — is built at write time, and
    keeping the two apart is what stops a page from being drawn in a layout called `scanned`.
    """
    for index, document in enumerate(
        synth_corpus.documents(seed=seed, per_tier=per_tier, tiers=tiers)
    ):
        yield document, rungs[index % per_tier % len(rungs)]


def generate(
    out_dir: Path,
    *,
    seed: int = synth_corpus.DEFAULT_SEED,
    per_tier: int = synth_corpus.DEFAULT_PER_TIER,
    tiers: tuple[Tier, ...] = TIERS,
    rungs: Sequence[Rung] = RUNGS,
    progress: Callable[[Entry], None] | None = None,
) -> list[Entry]:
    """Write the scanned corpus and its manifest, returning the index that was written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[Entry] = []
    layouts: dict[str, str] = {}
    for document, rung in documents(seed=seed, per_tier=per_tier, tiers=tiers, rungs=rungs):
        layouts[document.doc_id] = document.template
        entry = synth_corpus.write_document(
            _as_manifest_sees_it(document, rung), out_dir, draw=_scanner(document, rung)
        )
        entries.append(entry)
        if progress is not None:
            progress(entry)
    synth_corpus.write_index(out_dir, entries, _provenance(
        entries, seed=seed, per_tier=per_tier, tiers=tiers, rungs=rungs, layouts=layouts,
    ))
    return entries


def _scanner(original: Document, rung: Rung) -> Callable[[Document], scanner.Scan]:
    """A `Draw` that ignores its argument, because the one it needs is the one it was given.

    `write_document` passes the manifest's view of the document, whose `template` is the rung; the
    page has to be printed from the layout view, which is `original`. Closing over it is what keeps
    the two views from having to be the same object.
    """
    return lambda _: scanner.render(original, rung)


def _as_manifest_sees_it(document: Document, rung: Rung) -> Document:
    return Document(
        doc_id=document.doc_id,
        tier=document.tier,
        template=rung.name,
        seed=document.seed,
        invoice=document.invoice,
        context=document.context,
        overlay=document.overlay,
    )


def _provenance(
    entries: Sequence[Entry],
    *,
    seed: int,
    per_tier: int,
    tiers: tuple[Tier, ...],
    rungs: Sequence[Rung],
    layouts: dict[str, str],
) -> dict[str, Any]:
    """M2's block, plus what a rasterised byte depends on that a printed one does not.

    `pypdfium2` decides what a page looks like as pixels and `Pillow` decides what the JPEG of it
    is; either one changing rewrites every hash in this manifest without a line of this repository
    changing. That is the same argument the font hashes make, and it is why they are recorded rather
    than assumed.
    """
    base = asdict(synth_corpus.provenance(
        seed=seed, per_tier=per_tier, tiers=tiers, documents=len(entries),
    ))
    return {
        **base,
        "renderer": "scanned",
        "rungs": [asdict(rung) for rung in rungs],
        "layouts": layouts,
        "pypdfium2_version": _version("pypdfium2"),
        "pillow_version": _version("pillow"),
    }


def _version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:  # pragma: no cover — only from a bare checkout
        return "unknown"
