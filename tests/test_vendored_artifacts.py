"""The vendored artifacts must be the ones their provenance says they are.

`CLAUDE.md` says vendored artifacts are pinned by hash, and both `PROVENANCE.md` files carry
SHA-256 tables — but nothing was checking them, so the pin was documentation rather than a
constraint. The gap is specific: `assets/fonts/PROVENANCE.md` claims a substituted font is a red
test because `test_synth_render.py` asserts diacritics survive. That holds for a *missing* font,
which fails registration outright; it does not hold for a *substituted* one, because any DejaVu
release prints `ą` while changing every `pdf_sha256` in every manifest ever produced.

The expected digests are read out of the provenance documents rather than repeated here, so the
document stays the single place a re-vendor has to update — and a re-vendor that updates the files
but not the table fails just as loudly as one that does the reverse.
"""

from __future__ import annotations

import hashlib
import re

from conftest import REPO_ROOT

FONT_PROVENANCE = REPO_ROOT / "src" / "doc_extract" / "assets" / "fonts" / "PROVENANCE.md"
SCHEMA_PROVENANCE = REPO_ROOT / "schemas" / "PROVENANCE.md"

#: `| `name.ttf` | 757 076 B | `<64 hex>` |` — the shape both documents use for a file table.
_TABLE_ROW = re.compile(
    r"^\|\s*`(?P<name>[^`]+\.(?:ttf|xsd))`\s*\|[^|]*\|\s*`(?P<sha>[0-9a-f]{64})`\s*\|",
    re.MULTILINE,
)

#: `fa3.xsd` is described in a key/value table under its own heading rather than in a file table,
#: so its digest is picked up separately.
_KEYED_SHA = re.compile(r"^\|\s*SHA-256\s*\|\s*`(?P<sha>[0-9a-f]{64})`\s*\|", re.MULTILINE)

#: Every file the two documents pin, so a regex that silently stopped matching cannot leave this
#: suite green. These six are what `CLAUDE.md` names: the four XSDs and the two fonts. The vendored
#: `LICENSE` carries a digest too, but it has no bearing on a rendered byte or a parsed schema.
EXPECTED = {
    "DejaVuSans.ttf", "DejaVuSans-Bold.ttf",
    "fa3.xsd", "StrukturyDanych_v10-0E.xsd",
    "ElementarneTypyDanych_v10-0E.xsd", "KodyKrajow_v10-0E.xsd",
}


def declared() -> dict[str, str]:
    """Filename -> the SHA-256 its provenance document records for it."""
    found = {}
    for document, directory in (
        (FONT_PROVENANCE, FONT_PROVENANCE.parent),
        (SCHEMA_PROVENANCE, SCHEMA_PROVENANCE.parent),
    ):
        text = document.read_text(encoding="utf-8")
        for match in _TABLE_ROW.finditer(text):
            found[match.group("name")] = match.group("sha")
        if (keyed := _KEYED_SHA.search(text)) is not None:
            heading = re.search(r"^## `(?P<name>[^`]+)`", text, re.MULTILINE)
            if heading is not None:
                found[heading.group("name")] = keyed.group("sha")
        assert directory.is_dir()
    return found


def test_the_provenance_documents_pin_every_artifact_that_matters():
    """A parse that quietly matched nothing would make the test below vacuously green."""
    missing = EXPECTED - set(declared())
    assert not missing, f"no SHA-256 found in PROVENANCE.md for {sorted(missing)}"


def test_every_vendored_artifact_matches_its_recorded_hash():
    """Changing a font changes every rendered byte; changing an XSD changes what `vocab.py` means.

    Both are intended to be possible — as a commit that updates the file, the table and the corpus
    together. What must not be possible is one of the three moving on its own.
    """
    wrong = []
    for name, expected in sorted(declared().items()):
        directory = FONT_PROVENANCE.parent if name.endswith(".ttf") else SCHEMA_PROVENANCE.parent
        path = directory / name
        if not path.exists():
            wrong.append(f"{name}: recorded in PROVENANCE.md but not vendored")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            wrong.append(f"{name}: PROVENANCE.md says {expected[:12]}…, file is {actual[:12]}…")
    assert not wrong, wrong
