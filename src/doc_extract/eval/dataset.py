"""The corpus as the scorer sees it: gold, page, and the hashes that tie a result to both.

The generator already writes a manifest with a SHA-256 per artifact. This module is the other half
of that bargain — it *checks* them, on every read, and refuses to score a document whose bytes are
not the bytes the manifest attests to. A corpus regenerated with a different seed, a different
reportlab, or a different font produces different pages and different hashes, and a run that scored
the new pages while reporting the old manifest would be a result nobody could reproduce and nobody
could catch.

**The gold is read from the XML on disk, not rebuilt from the seed.** Both would work, and reading
is the stronger claim: it scores against the artifact that was actually shipped, through
`fa3_xml.gold_from_xml`, whose round trip M2 asserts to be the identity. Rebuilding from the seed
would score against what the generator would produce *now*, which is a different statement the
moment any generator code changes.

Nothing here reads a PDF or an XML until it is asked to. A run over 108 documents holds one page in
memory at a time, and a scorer that only needs the gold never opens a PDF at all.
"""

from __future__ import annotations

import hashlib
import io
import json
import zlib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from doc_extract.extract.client import PageImage
from doc_extract.schema.ksef import Invoice
from doc_extract.source import document as source_document
from doc_extract.source import raster
from doc_extract.source.document import SourceDocument
from doc_extract.synth import fa3_xml
from doc_extract.synth.corpus import MANIFEST_NAME, PROVENANCE_NAME


class CorpusError(RuntimeError):
    """The corpus on disk is not the corpus the manifest describes."""


@dataclass(frozen=True, slots=True)
class Case:
    """One document of the corpus: where it is, what it hashes to, and how to read either half."""

    doc_id: str
    #: The axes this corpus varies, in the order it declares them, as `(name, value)` pairs.
    #:
    #: **A pair rather than two named columns, because the axes are a property of the corpus and
    #: not of this class.** A generated corpus varies difficulty and layout and calls them `tier`
    #: and `template`; `degrade/` already repurposes `template` to mean *which scanner rung*,
    #: which is the tell that the column was a slot all along. A corpus of documents nobody
    #: generated has neither and wants others — who issued it, whether it is a scan — and the
    #: report groups by whatever is here rather than by two names fixed in this file.
    facets: tuple[tuple[str, str], ...]
    seed: int
    directory: Path
    xml: str
    pdf: str
    xml_sha256: str
    pdf_sha256: str
    pages: int

    def facet(self, name: str) -> str:
        """One axis's value, or the empty string where this corpus does not vary that axis."""
        return dict(self.facets).get(name, "")

    @property
    def tier(self) -> str:
        """The difficulty band, for the corpora that have one. Empty where a corpus has none."""
        return self.facet("tier")

    @property
    def template(self) -> str:
        return self.facet("template")

    @property
    def xml_path(self) -> Path:
        return self.directory / self.xml

    @property
    def pdf_path(self) -> Path:
        return self.directory / self.pdf

    def gold(self) -> Invoice:
        """The ground truth, read back out of the FA(3) document the corpus shipped."""
        return fa3_xml.gold_from_xml(self._verified(self.xml_path, self.xml_sha256).decode("utf-8"))

    def pdf_bytes(self) -> bytes:
        """The page's bytes, verified against the manifest. The one place either reader starts."""
        return self._verified(self.pdf_path, self.pdf_sha256)

    def source(self, data: bytes | None = None) -> SourceDocument:
        """The page, as text with a span per word and per cell. No model, no network.

        `data` lets a caller that already holds the verified bytes hand them back rather than have
        the file read and hashed a second time — which a vision run, needing both readings of one
        page, otherwise would.
        """
        return source_document.read(self.pdf_bytes() if data is None else data)

    def images(self, data: bytes | None = None) -> tuple[PageImage, ...]:
        """The page as pictures of itself, one per printed page, ready to send to a model.

        Rasterised from the same verified bytes `source()` reads, so a vision arm and a text arm are
        demonstrably looking at the same document rather than at two files that happen to share a
        name. PNG rather than JPEG: the corpus already carries whatever damage it is meant to carry,
        and a second lossy encoding on the way out would add damage no rung asked for — at the cost
        of an upload several times the size of the JPEG already inside the page.
        """
        pages = raster.for_vision(self.pdf_bytes() if data is None else data)
        return tuple(PageImage(media_type="image/png", data=_png(page)) for page in pages)

    def _verified(self, path: Path, expected: str) -> bytes:
        try:
            data = path.read_bytes()
        except OSError as error:
            raise CorpusError(
                f"{self.doc_id}: {path} could not be read; rebuild the corpus with "
                "`python -m doc_extract.synth --out <dir>`"
            ) from error
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise CorpusError(
                f"{self.doc_id}: {path.name} hashes to {actual[:16]}… but the manifest says "
                f"{expected[:16]}…; the corpus on disk is not the one this run would report"
            )
        return data


@dataclass(frozen=True, slots=True)
class Corpus:
    """The manifest, checked, plus the provenance block a report has to carry."""

    directory: Path
    cases: tuple[Case, ...]
    provenance: dict[str, Any]
    #: Every document the manifest describes, which is not the same as every document *this* object
    #: holds once `select` has been called. Coverage is asserted against the manifest, so a subset
    #: stays a subset in the report instead of becoming a complete run over a smaller corpus.
    manifest_ids: tuple[str, ...] = ()

    @property
    def doc_ids(self) -> tuple[str, ...]:
        return tuple(case.doc_id for case in self.cases)

    @property
    def expected(self) -> tuple[str, ...]:
        """What a complete run would have scored. The denominator of coverage."""
        return self.manifest_ids or self.doc_ids

    def select(self, *, tiers: Sequence[str] = (), limit: int | None = None) -> Corpus:
        """A subset that remembers what it is a subset of.

        The manifest's document list travels with it, so scoring the result reports incomplete
        coverage and refuses to be a headline number unless the caller says `allow_partial` —
        which is the whole point. A subset that forgot it was a subset is the failure the coverage
        rule exists to prevent.
        """
        chosen = [case for case in self.cases if not tiers or case.tier in tiers]
        if limit is not None:
            chosen = chosen[:limit]
        return Corpus(
            directory=self.directory,
            cases=tuple(chosen),
            provenance=self.provenance,
            manifest_ids=self.expected,
        )


def load(directory: Path) -> Corpus:
    """Read a corpus manifest. Nothing is hashed here; every read verifies its own artifact."""
    manifest = directory / MANIFEST_NAME
    if not manifest.exists():
        raise CorpusError(
            f"no {MANIFEST_NAME} in {directory}; build the corpus with "
            "`python -m doc_extract.synth --out " + str(directory) + "`"
        )
    rows = list(_rows(manifest))
    cases = tuple(_case(row, directory) for row in rows)
    if not cases:
        raise CorpusError(f"{manifest} describes no documents")
    return Corpus(
        directory=directory,
        cases=cases,
        provenance=_provenance(directory) | _derived_seeds(rows),
        manifest_ids=tuple(case.doc_id for case in cases),
    )


def _derived_seeds(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """How many documents carry a seed this module invented rather than the generator's.

    Recorded rather than assumed, because `_seed` derives one for a manifest that has none and a
    reader would otherwise have no way to tell the two apart. A generated corpus has a seed on
    every row and this contributes nothing, so the committed runs' provenance blocks do not move.
    """
    derived = sum(1 for row in rows if row.get("seed") is None)
    return {"derived_seeds": derived} if derived else {}


def _rows(manifest: Path) -> Iterator[dict[str, Any]]:
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def _case(row: dict[str, Any], directory: Path) -> Case:
    return Case(
        doc_id=row["doc_id"],
        facets=_facets(row),
        seed=_seed(row),
        directory=directory,
        xml=row["xml"],
        pdf=row["pdf"],
        xml_sha256=row["xml_sha256"],
        pdf_sha256=row["pdf_sha256"],
        pages=row["pages"],
    )


def _facets(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    """The row's axes, declared or inferred.

    A manifest may name its axes outright — `"facets": {"issuer": "...", "legibility": "..."}` —
    and a generated one does not, so `tier` and `template` are read as the two axes it varies. The
    inference is here rather than in the generator so that the 24 committed runs keep rendering the
    same two tables from the same manifests, which is the check that this generalisation was free.
    """
    declared = row.get("facets")
    if declared is not None:
        return tuple((str(name), str(value)) for name, value in declared.items())
    return tuple(
        (name, str(row[name])) for name in ("tier", "template") if row.get(name) is not None
    )


def _seed(row: dict[str, Any]) -> int:
    """The seed the generator used, or one derived from the document's name.

    A document nobody generated has no seed, and `eval/run.py` gives every task one — `noisy` and
    `corrupt` need it to be reproducible. Deriving one keeps every baseline runnable on every
    corpus, which is this project's rule that a baseline with its own code path is measuring its
    own code path.

    `zlib.crc32` for the same reason `synth/corpus.py` uses it: `hash()` is randomised per
    interpreter run, so a "reproducible" baseline would not be. It is **not** the generator's
    formula and must not be read as one — `synth.corpus` mixes in the corpus seed
    (`(corpus_seed * 1_000_003 + crc32(doc_id)) % 2**31`), which this has no access to and would
    have no meaning without. Two documents with the same name in a generated and a hand-written
    corpus therefore get different seeds, which is correct: one is the number that produced the
    document and the other is a number invented so a baseline can run.

    `load` records how many rows carry a derived seed in the corpus's provenance block, so the
    distinction is in the artifact rather than only here.
    """
    recorded = row.get("seed")
    return int(recorded) if recorded is not None else zlib.crc32(row["doc_id"].encode("utf-8"))


def _provenance(directory: Path) -> dict[str, Any]:
    """The generator's own record of what built the corpus, copied into the run verbatim.

    Missing rather than fatal: a corpus assembled by hand for a test has no provenance block, and
    refusing to score it would make the scorer harder to test than the thing it scores. The report
    prints what is there, so an empty block is visible rather than silently absent.
    """
    path = directory / PROVENANCE_NAME
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
