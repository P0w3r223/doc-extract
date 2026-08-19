"""Assemble the documents into a corpus on disk, with an index that makes it checkable.

The corpus is **not committed**. It is a function of one integer, so a seed in the manifest is a
smaller and more honest artifact than several hundred PDFs in git history; anyone can rebuild the
identical bytes, and `.gitignore` keeps the outputs out.

Two choices here are load-bearing for what M4 can conclude:

**Templates rotate within each tier, not across the corpus.** If a tier were rendered in a single
layout, a per-tier accuracy drop could equally be a per-template drop, and no table could separate
them. Rotating means every tier appears in every layout roughly equally often.

**Every document's seed is derived from the corpus seed and the document's own name**, not drawn
from a running generator. Adding a tier, or generating fewer documents, therefore leaves every
other document byte-identical — which is what makes a result comparable across two runs of the
generator rather than merely reproducible within one.
"""

from __future__ import annotations

import hashlib
import json
import zlib
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any, Protocol

from doc_extract.schema.generate_vocab import XSD_PATH
from doc_extract.synth import fa3_xml, render
from doc_extract.synth.build import Document, build
from doc_extract.synth.tiers import TIERS, Tier

DEFAULT_SEED = 20260818
DEFAULT_PER_TIER = 12

MANIFEST_NAME = "manifest.jsonl"
PROVENANCE_NAME = "manifest.meta.json"

class Page(Protocol):
    """A rendered document: the bytes, and the one fact about them the manifest needs.

    Structural rather than a shared base class, so M7's foreign renderer satisfies it by having the
    right shape instead of by importing this module. `render.Rendered` is the implementation M2 and
    M6 pass; the foreign package has its own, and that separation is the point.
    """

    data: bytes
    pages: int


#: How a document becomes a page. Anything returning bytes and a page count satisfies it, which is
#: what lets M7's foreign renderer reuse the manifest machinery without sharing a line of layout.
Draw = Callable[[Document], Page]


@dataclass(frozen=True, slots=True)
class Entry:
    """One row of the manifest — enough to find a document, and to prove it was not edited."""

    doc_id: str
    tier: str
    template: str
    seed: int
    kind: str
    currency: str
    number: str
    lines: int
    total_gross: str
    xml: str
    pdf: str
    xml_sha256: str
    pdf_sha256: str
    pages: int


@dataclass(frozen=True, slots=True)
class Provenance:
    """What the corpus was built *from* — the inputs every `pdf_sha256` silently depends on.

    The fonts' own `PROVENANCE.md` makes the argument for them: changing one changes every
    rendered byte, and the manifest is what records which corpus a result was computed on. The same
    is true of reportlab, whose output is not a stable format across releases, and of the seed and
    the tier set, which decide which invoices exist at all. Without these, two runs whose hashes
    differ give no way to tell a real change from a `pip install -U` in between — the manifest
    would record *that* the corpus changed while staying silent on *why*.
    """

    corpus_seed: int
    per_tier: int
    tiers: tuple[str, ...]
    documents: int
    doc_extract_version: str
    reportlab_version: str
    fa3_xsd_sha256: str
    fonts_sha256: dict[str, str] = field(default_factory=dict)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def provenance(*, seed: int, per_tier: int, tiers: tuple[Tier, ...], documents: int) -> Provenance:
    """The build inputs, read at generation time rather than recorded by hand."""
    return Provenance(
        corpus_seed=seed,
        per_tier=per_tier,
        tiers=tuple(tier.name for tier in tiers),
        documents=documents,
        doc_extract_version=_version("doc-extract"),
        reportlab_version=_version("reportlab"),
        fa3_xsd_sha256=_sha256(XSD_PATH),
        fonts_sha256={
            name: _sha256(render.FONT_DIR / f"{name}.ttf") for name in (render.REGULAR, render.BOLD)
        },
    )


def _version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:  # pragma: no cover — only when run from a bare checkout
        return "unknown"


def documents(*, seed: int = DEFAULT_SEED, per_tier: int = DEFAULT_PER_TIER,
              tiers: tuple[Tier, ...] = TIERS) -> Iterator[Document]:
    """Every document of the corpus, in a stable order, without touching the filesystem."""
    for tier in tiers:
        for index in range(per_tier):
            doc_id = f"{tier.name}-{index:04d}"
            yield build(
                tier,
                seed=_document_seed(seed, doc_id),
                doc_id=doc_id,
                template=render.TEMPLATES[index % len(render.TEMPLATES)],
            )


def generate(out_dir: Path, *, seed: int = DEFAULT_SEED, per_tier: int = DEFAULT_PER_TIER,
             tiers: tuple[Tier, ...] = TIERS) -> list[Entry]:
    """Write the corpus and its manifest, returning the index that was written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = [write_document(document, out_dir) for document in
               documents(seed=seed, per_tier=per_tier, tiers=tiers)]
    built = provenance(seed=seed, per_tier=per_tier, tiers=tiers, documents=len(entries))
    write_index(out_dir, entries, asdict(built))
    return entries


def write_index(out_dir: Path, entries: Sequence[Entry], built: Mapping[str, Any], *,
                keep: Sequence[str] = ()) -> None:
    """The manifest, the provenance block, and the removal of anything neither describes.

    Shared with M6's attack suite, which writes a corpus of its own into a directory of its own and
    has exactly the same obligation: regenerating with fewer documents used to leave the old files
    in place with nothing in the manifest describing them, and anything globbing `*.pdf` would then
    read a corpus larger than the one the manifest attests to — the failure the manifest exists to
    make impossible. `keep` names the extra files a caller writes beside the corpus, which are
    described by that caller rather than by the manifest.
    """
    described = {entry.xml for entry in entries} | {entry.pdf for entry in entries}
    described |= {MANIFEST_NAME, PROVENANCE_NAME, *keep}
    for stale in out_dir.iterdir():
        if stale.is_file() and stale.name not in described:
            stale.unlink()

    (out_dir / MANIFEST_NAME).write_bytes(
        "".join(json.dumps(asdict(entry), ensure_ascii=False) + "\n" for entry in entries)
        .encode("utf-8")
    )
    #: Kept beside the rows rather than as a header line, so `manifest.jsonl` stays one shape per
    #: line and anything reading it can go on treating every line as a document.
    (out_dir / PROVENANCE_NAME).write_bytes(
        (json.dumps(built, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )


def write_document(document: Document, out_dir: Path, *, draw: Draw = render.render) -> Entry:
    """One document's XML and PDF on disk, plus the manifest row that attests to both.

    `draw` is how a corpus other than M2's gets written by this function rather than beside it. M6's
    attacked corpus keeps the default — an attacked page is this renderer's page with a string added
    — and M7's foreign corpus passes its own, because the whole of what it varies is the page. The
    manifest, the hashing and the byte-level write are not presentation and are not worth a second
    copy: a second one is a second place for a corpus to become undescribed by its own index.
    """
    xml_text = fa3_xml.to_xml(document)
    pdf = draw(document)

    xml_path = out_dir / f"{document.doc_id}.xml"
    pdf_path = out_dir / f"{document.doc_id}.pdf"
    #: Written as bytes, not text: `write_text` would translate newlines to CRLF on Windows, so
    #: the same seed would produce a different file — and a different hash — on a different
    #: platform. A corpus that is only reproducible per operating system is not reproducible.
    xml_bytes = xml_text.encode("utf-8")
    xml_path.write_bytes(xml_bytes)
    pdf_path.write_bytes(pdf.data)

    invoice = document.invoice
    return Entry(
        doc_id=document.doc_id,
        tier=document.tier,
        template=document.template,
        seed=document.seed,
        kind=invoice.kind,
        currency=invoice.currency,
        number=invoice.number,
        lines=len(invoice.lines),
        total_gross=f"{invoice.total_gross:.2f}",
        xml=xml_path.name,
        pdf=pdf_path.name,
        xml_sha256=hashlib.sha256(xml_bytes).hexdigest(),
        pdf_sha256=hashlib.sha256(pdf.data).hexdigest(),
        pages=pdf.pages,
    )


def _document_seed(corpus_seed: int, doc_id: str) -> int:
    """A per-document seed that depends on the document's name, not on generation order.

    `zlib.crc32` is used rather than `hash()`, which is randomised per interpreter run and would
    make the corpus irreproducible across processes — the one thing the seed exists to prevent.
    """
    return (corpus_seed * 1_000_003 + zlib.crc32(doc_id.encode("utf-8"))) % (2**31)
