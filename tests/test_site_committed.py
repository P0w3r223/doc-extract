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
  The allowance is one-directional — the *committed* page must still carry the block — because
  otherwise a rebuild in a checkout without the corpus would silently delete the milestone's
  headline and leave every test here green.

And because that table restates a definition the scorer already owns, its totals are reconciled
against what `gate` reports for the same run and the same signal. They disagreed once, by exactly
the spurious values, which is the failure a page of derived figures is most exposed to: a second
implementation of a rule the first one already has.
"""

from __future__ import annotations

import pathlib
import re
import sys
from html.parser import HTMLParser

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
def test_site_tables_scroll():
    """A table wider than a phone must scroll inside its own box, not carry the page with it.

    Five of this page's thirteen tables are wider than the 335px content box a 375px viewport
    leaves, and the widest — fourteen columns of per-baseline figures at 448px — took the whole
    document 93px sideways. `width: 100%` cannot help: a table is never narrower than its columns
    need.

    The two premises that make one substitution over the assembled page safe are asserted rather
    than assumed, because both are properties of how the tables happen to be written today and
    neither is enforced anywhere else: every table is a bare `<table>` with no attributes, and no
    table contains another. A table written any other way would escape the wrapper silently, and
    this is the only thing that would notice.
    """
    import build_index

    committed = PAGE.read_text(encoding="utf-8")

    assert "<table " not in committed, (
        "a table with attributes would not match the wrapper's pattern"
    )

    class _Tables(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.wrappers: list[str] = []
            self.open_tables = 0
            self.tables = 0
            self.unwrapped = 0
            self.nested = 0

        def handle_starttag(self, tag, attrs):
            if tag == "table":
                self.tables += 1
                if self.open_tables:
                    self.nested += 1
                self.open_tables += 1
                if "table-wrap" not in self.wrappers:
                    self.unwrapped += 1
            elif tag == "div":
                self.wrappers.append(dict(attrs).get("class", ""))

        def handle_endtag(self, tag):
            if tag == "table":
                self.open_tables = max(0, self.open_tables - 1)
            elif tag == "div" and self.wrappers:
                self.wrappers.pop()

    parser = _Tables()
    parser.feed(committed)

    assert parser.tables == 13, "the count moved — check the new table is wrapped like the others"
    assert parser.nested == 0, "a nested table would end the wrapper's non-greedy match early"
    assert parser.unwrapped == 0, f"{parser.unwrapped} table(s) can drag the page sideways"
    # The wrapper is inert without the rule that makes it scroll.
    assert re.search(r"\.table-wrap\s*\{\s*overflow-x:\s*auto", committed)
    # And the rule has to survive `TEMPLATE.format`, where a literal brace must be doubled.
    assert ".table-wrap {{ overflow-x: auto; }}" in build_index.TEMPLATE


@pytest.mark.skipif(not PAGE.exists(), reason="the site has not been built in this checkout")
def test_the_way_back_is_a_page_a_reader_can_open():
    """The one link off this page has to lead somewhere a visitor can actually reach.

    It did not. The footer pointed at `P0w3r223/current_projects`, the index repository, which is
    private — so the only route from this page to the rest of the work answered a stranger with a
    404. That is worse than having no link at all: a dead way back reads as a portfolio that has
    been taken down, rather than as a page that simply stands alone.

    The public index is the profile README, so the footer points at the profile.
    """
    import build_index

    committed = PAGE.read_text(encoding="utf-8")

    assert "current_projects" not in committed, (
        "the index repository is private — a link to it is a 404 for every reader"
    )
    assert f'href="{build_index.PROFILE}"' in committed


def test_a_table_is_wrapped_wherever_it_is_written():
    """The mechanism, on both shapes this file writes: one line, and opened across several."""
    import build_index

    one_line = "<table><thead><tr><th>a</th></tr></thead><tbody></tbody></table>"
    multi_line = "<table>\n<thead><tr><th>a</th></tr></thead>\n<tbody></tbody>\n</table>"

    for markup in (one_line, multi_line):
        assert build_index._scrollable_tables(markup) == f'<div class="table-wrap">{markup}</div>'

    two = build_index._scrollable_tables(one_line + "<p>between</p>" + one_line)
    assert two.count('<div class="table-wrap">') == 2, (
        "each table gets its own box, not one around both"
    )
    assert "<p>between</p>" in two


CORPUS = ROOT / "data" / "scanned"

#: Every committed run over the scanned corpus, not just the control. The control is the *worst*
#: arm to check a definition of "wrong" against: it answers the gold, so it has no wrong values and
#: no spurious ones, and the two definitions this test exists to reconcile agree vacuously on it.
SCANNED_RUNS = sorted(
    directory.name
    for directory in (ROOT / "results").glob("scanned-*")
    if (directory / "predictions.jsonl").exists()
) if (ROOT / "results").is_dir() else []


@pytest.mark.skipif(
    not (CORPUS / "manifest.jsonl").exists() or not SCANNED_RUNS,
    reason="the scanned corpus or a run over it is not present in this checkout",
)
@pytest.mark.parametrize("name", SCANNED_RUNS)
def test_the_pages_grounding_split_totals_what_the_gate_reports(name):
    """The page splits one signal by rung; `gate.md` reports the same signal whole. They must agree.

    They did not. `_grounding_by_rung` restated "a wrong asserted value" as one outcome, while
    `eval/selective.py` defines it as two — a value that disagrees with the document *or* one the
    document does not carry at all. Twenty-three spurious instances went missing from a table
    printed beside the gate report that contained them. Comparing the totals is what makes the two
    definitions one definition.
    """
    import build_index

    from doc_extract.degrade.corpus import documents as scanned_documents
    from doc_extract.eval import dataset, predictions, run

    corpus = dataset.load(CORPUS)
    directory = ROOT / "results" / name
    records = predictions.read(directory / "predictions.jsonl")
    curve = run.gate(corpus, records)
    grounding = next(signal for signal in curve.signals if signal.name == "grounding")

    gold = {
        document.doc_id: build_index._with_template(document, rung.name)
        for document, rung in scanned_documents()
    }
    cases = {case.doc_id: case for case in corpus.cases}
    rows = build_index._grounding_by_rung(directory, cases, gold)
    total: dict[str, int] = {}
    for counts in rows.values():
        for key, value in counts.items():
            total[key] = total.get(key, 0) + value

    assert total.get("TP", 0) == grounding.true_positive
    assert total.get("FP", 0) == grounding.false_positive
    assert total.get("FN", 0) == grounding.false_negative
    assert total.get("TN", 0) == grounding.true_negative


@pytest.mark.skipif(not PAGE.exists(), reason="the site has not been built in this checkout")
def test_the_committed_page_carries_the_block_the_comparison_forgives():
    """The exemption is one-directional, and without this it is a hole rather than an allowance.

    A page built in a checkout without `data/scanned` drops the whole fenced block — the oracle's
    grounding split and the model's, which is M7d's headline — and the comparison above would stay
    green, because it strips a fence neither side has. So the *committed* page has to carry it even
    though a freshly rendered one need not, and the width of what is stripped is checked here rather
    than assumed: everything outside the fence must survive `_comparable`.
    """
    import build_index

    committed = PAGE.read_text(encoding="utf-8")

    assert build_index.CORPUS_DEPENDENT in committed, (
        "docs/index.html was built without data/scanned — rebuild it with the corpus present"
    )
    assert build_index.CORPUS_DEPENDENT_END in committed
    assert "When the page is a picture" in _comparable(committed), (
        "the fence is wider than the block it is meant to cover"
    )
