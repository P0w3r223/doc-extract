"""`docs/index.html` is committed and generated, so it can be stale — and it is a page of numbers.

Every figure on that page is computed from the vendored schema, the invariant rules and the
committed prediction files, which is the whole of its argument: a portfolio page whose numbers were
transcribed by hand is exactly the artifact this project argues against. Nothing was checking that
the committed bytes are still what the generator produces, so a run re-scored without rebuilding the
site would leave the page quoting a figure no artifact in the repository contains.

Two things are allowed to differ, and both are stated rather than tolerated silently:

* **The commit in the footer.** It is `HEAD` at build time, so it names the commit *before* the one
  that carries the page — regenerating in a test would compare a hash against itself and assert
  nothing.
* **The grounding-per-rung table.** It is the one figure on the page that needs a corpus on disk,
  because grounding resolves a value against page text and no artifact records what a page says.
  `data/scanned` is not committed, so a checkout without it renders the section without that table.
"""

from __future__ import annotations

import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "index.html"

#: The generator lives in `docs/`, which is not a package and not on the path.
sys.path.insert(0, str(ROOT / "docs"))

def _comparable(html: str) -> str:
    """The page with the two legitimately varying parts removed.

    The corpus-dependent block is found by the fence `build_index` prints around it rather than by
    a pattern over its prose: a reworded paragraph would quietly widen a prose pattern, and what
    this test forgives has to stay exactly one block wide.
    """
    import build_index

    without_commit = re.sub(
        r"built from the tree after\n  <code>[0-9a-f]+</code>",
        "built from the tree after <code>COMMIT</code>",
        html,
    )
    opening = re.escape(build_index.CORPUS_DEPENDENT)
    closing = re.escape(build_index.CORPUS_DEPENDENT_END)
    return re.sub(f"{opening}.*?{closing}", "", without_commit, flags=re.DOTALL)


@pytest.mark.skipif(not PAGE.exists(), reason="the site has not been built in this checkout")
def test_the_committed_page_is_what_the_generator_produces():
    import build_index

    rendered = build_index.build()
    committed = PAGE.read_text(encoding="utf-8")

    assert _comparable(rendered) == _comparable(committed), (
        "docs/index.html is stale — re-run `python docs/build_index.py`"
    )


@pytest.mark.skipif(not PAGE.exists(), reason="the site has not been built in this checkout")
def test_the_page_carries_the_scan_result_it_is_supposed_to():
    """A guard on the exemption above: the removed block must be absent, not the whole section."""
    committed = PAGE.read_text(encoding="utf-8")

    assert "When the page is a picture" in committed
