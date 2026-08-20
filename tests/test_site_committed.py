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
