"""What makes the foreign corpus a measurement rather than a second pile of PDFs.

Three claims, and the package is worth nothing if any of them is false:

* **It is paired.** Document by document, the gold is the synthetic corpus's gold. If it were not,
  a difference between two runs would be a difference between two sets of invoices and the
  attribution to the *page* would be unavailable.
* **It is foreign.** None of the labels the fitted reader keys on is on these pages, and the fitted
  reader is measurably worse for it. A shared `Do zapłaty:` would leave the most valuable field
  readable and the held-out claim would quietly stop being true.
* **It is still solvable.** `tests/test_foreign_render.py` asserts every gold value is printed; here
  the gold is grounded against its own foreign page, which is the control that caught four distinct
  bugs when `ground/` was built and would catch a page that printed a value in a form nothing can
  resolve.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from doc_extract.eval import dataset, pattern
from doc_extract.foreign import corpus as foreign_corpus
from doc_extract.foreign import render as foreign_render
from doc_extract.foreign.dialect import DIALECTS, TEMPLATES
from doc_extract.ground.resolve import resolve as ground
from doc_extract.source import document as source_document
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth import render as synth_render
from doc_extract.synth.tiers import BY_NAME as TIERS

#: The literals `eval/pattern.py` keys on. They are written out here rather than imported because
#: this test is *about* those exact strings: it asserts a foreign page does not carry them, and a
#: test that read them from the module it is checking would pass if both changed together.
FITTED_LABELS = (
    "Numer faktury:", "Data wystawienia:", "Data sprzedaży:", "Do zapłaty:", "Rachunek:",
    "Termin płatności:", "Forma płatności:", "Sprzedawca", "Nabywca", "Adnotacje:",
    "Nazwa towaru lub usługi", "Wartość netto", "Kwota VAT",
)

TWO_TIERS = (TIERS["clean"], TIERS["mixed_rates"])


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> Path:
    directory = tmp_path_factory.mktemp("foreign")
    foreign_corpus.generate(directory, per_tier=1, tiers=TWO_TIERS)
    return directory


def test_the_gold_is_the_synthetic_corpus_s_gold_document_for_document():
    """The one claim the whole comparison rests on: only the page moved."""
    ours = list(foreign_corpus.documents(per_tier=2, tiers=TWO_TIERS))
    theirs = list(synth_corpus.documents(per_tier=2, tiers=TWO_TIERS))

    assert [document.doc_id for document in ours] == [d.doc_id for d in theirs]
    for mine, theirs_ in zip(ours, theirs, strict=True):
        assert mine.invoice == theirs_.invoice, mine.doc_id
        assert mine.seed == theirs_.seed
        assert mine.tier == theirs_.tier
        assert mine.template != theirs_.template


def test_the_three_dialects_are_three_vocabularies_and_not_one():
    """Three layouts sharing one set of words would be one held-out page printed three ways."""
    for field in ("seller", "buyer", "payable", "number", "issued", "account"):
        said = [getattr(dialect, field) for dialect in DIALECTS]
        assert len(set(said)) == len(DIALECTS), f"{field} is said the same way by two dialects"


def test_the_layouts_share_no_name_with_the_synthetic_ones():
    """A shared name would make a per-template table two corpora's rows under one heading."""
    assert not set(TEMPLATES) & set(synth_render.TEMPLATES)


def test_no_foreign_page_carries_a_label_the_fitted_reader_keys_on():
    """The held-out claim, checked against the page rather than argued in a docstring."""
    for tier in TWO_TIERS:
        for template in TEMPLATES:
            text = source_document.read(
                foreign_render.render(_one(tier, template)).data
            ).text
            found = [label for label in FITTED_LABELS if label in text]
            assert not found, f"{tier.name}/{template} still prints {found}"


def _one(tier, template):
    from doc_extract.synth.build import build
    return build(tier, seed=4242, doc_id=f"{tier.name}-{template}", template=template)


def test_the_fitted_reader_loses_on_a_page_it_was_not_fitted_to():
    """B2's 86.3 % is the number this corpus exists to put a bound on.

    Not an exact figure — that is what a run reports — but the direction has to hold, and a reader
    that scored the same on both pages would mean the labels it matches were never doing the work.
    """
    tier = TIERS["clean"]
    ours = pattern.read(source_document.read(
        foreign_render.render(_one(tier, TEMPLATES[0])).data
    ).text)
    theirs = pattern.read(source_document.read(
        synth_render.render(_one(tier, synth_render.TEMPLATES[0])).data
    ).text)

    assert _answered(theirs) > _answered(ours), "the fitted reader must do better on its own page"
    assert _answered(ours) < _answered(theirs) / 2, "and it must lose most of what it had"


def _answered(payload: dict) -> int:
    return sum(1 for value in payload.values() if value not in (None, "", [], {}))


def test_the_foreign_package_shares_no_presentation_with_the_synthetic_one():
    """The claim that this is a second renderer and not a re-skin, made checkable.

    `synth.build` is allowed — a `Document` is the data contract both sides read. `synth.render`,
    `synth.pools` and `synth.overlay` are not: they *are* the page, and importing any of them would
    make the held-out set a variation on the corpus it is meant to be held out from.
    """
    forbidden = {"doc_extract.synth.render", "doc_extract.synth.pools", "doc_extract.synth.overlay"}
    for module in ("render.py", "dialect.py", "__init__.py"):
        source = Path(foreign_render.__file__).with_name(module).read_text(encoding="utf-8")
        imported = {
            node.module for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert not imported & forbidden, f"foreign/{module} imports {imported & forbidden}"


def test_the_corpus_loads_and_says_which_renderer_drew_it(built):
    """A run that could not tell the two corpora apart would be a result nobody could reproduce."""
    loaded = dataset.load(built)

    assert len(loaded.cases) == len(TWO_TIERS)
    assert loaded.provenance["renderer"] == "foreign"
    assert set(loaded.provenance["templates"]) == set(TEMPLATES)
    assert {case.template for case in loaded.cases} <= set(TEMPLATES)


def test_the_gold_grounds_against_its_own_foreign_page(built):
    """The control. Gold read off the page it was printed on must resolve, or grounding is broken.

    This is the check that caught four distinct defects when `ground/` was built — a value the page
    prints in a form `surface` cannot produce comes back ungrounded, and on a run it would be
    reported as a model error rather than as a corpus that speaks a dialect nothing can read.
    """
    unresolved = []
    for case in dataset.load(built).cases:
        unresolved += [
            f"{case.doc_id}:{row.field}={row.value}"
            for row in ground(case.source(), case.gold())
            if row.suspicious
        ]
    assert not unresolved, unresolved[:8]
