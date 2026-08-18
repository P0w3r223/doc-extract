# Vendored font provenance

## `DejaVuSans.ttf`, `DejaVuSans-Bold.ttf`

| | |
|---|---|
| What | DejaVu Sans, regular and bold |
| Release | `dejavu-fonts-ttf-2.37` |
| Source | <https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.zip> |
| Retrieved | 2026-08-18 |
| Licence | Bitstream Vera / DejaVu — permissive, redistributable; full text in `LICENSE` beside these files |

| File | Size | SHA-256 |
|---|---|---|
| `DejaVuSans.ttf` | 757 076 B | `7da195a74c55bef988d0d48f9508bd5d849425c1770dba5d7bfc6ce9ed848954` |
| `DejaVuSans-Bold.ttf` | 705 684 B | `e6476c1b80502924294eed40894c5b18e06c181444ca953e5334262df9c27724` |
| `LICENSE` | 8 816 B | `7a083b136e64d064794c3419751e5c7dd10d2f64c108fe5ba161eae5e5958a93` |

## Why a font is vendored at all

The corpus generator renders Polish invoices, and Polish invoices are full of `ą ć ę ł ń ó ś ź ż`.

The fonts reportlab ships with cannot print them. Bitstream Vera — `reportlab/fonts/Vera.ttf`, the
only TrueType family in the wheel — is **missing twelve of the eighteen accented Polish letters**;
DejaVu exists precisely because it extended Vera to cover them. A corpus set in Vera would drop
those characters silently, which would make every generated document easier to read than a real one
in exactly the respect that matters for extraction.

The remaining options were a system font, which is not reproducible across machines or CI, or this:
a fixed release, pinned by hash, checked into the repository. `tests/test_synth_render.py` asserts
that diacritics survive into the rendered text layer, which catches a *missing* font — registration
fails outright. It does not catch a *substituted* one: any DejaVu release prints `ą` while changing
every `pdf_sha256` ever produced. `tests/test_vendored_artifacts.py` closes that by checking the
files against the digests in the table above, so this document is a constraint and not a claim.

They live inside the package (`src/doc_extract/assets/fonts/`) rather than beside it, because
rendering needs them at run time: found by walking up from `__file__`, they were only reachable
from an editable install.

## Re-vendoring

```bash
curl -sSL -o dejavu.zip \
  https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.zip
unzip -j dejavu.zip 'dejavu-fonts-ttf-2.37/ttf/DejaVuSans.ttf' \
                    'dejavu-fonts-ttf-2.37/ttf/DejaVuSans-Bold.ttf' \
                    'dejavu-fonts-ttf-2.37/LICENSE' -d src/doc_extract/assets/fonts/
sha256sum src/doc_extract/assets/fonts/*     # update the table above
pytest tests/test_synth_render.py tests/test_vendored_artifacts.py
```

Changing the font changes every rendered byte, and therefore every `pdf_sha256` in a corpus
manifest. That is intended: the manifest records which corpus a result was computed on.
