"""The grid, the corpus it becomes, and the two ways it could quietly stop measuring anything.

The first is **pairing**: every payload has to be printed on the same pages, or the per-payload
columns compare different invoices and the comparison means nothing. The second is **verification**:
a payload that did not survive rendering would sit in the denominator as a failed attack, which is
the one direction an attack success rate must not be wrong in.

The end-to-end test at the bottom is deliberately whole — build, run a baseline, join, report — on
two documents. It is the only place that proves an attacked corpus is an ordinary corpus as far as
`eval` is concerned, which is the design decision the whole milestone rests on.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doc_extract.attack import suite
from doc_extract.attack.payloads import BY_NAME, PAYLOADS, Payload
from doc_extract.attack.suite import SuiteError
from doc_extract.eval import dataset
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.overlay import PLACEMENTS
from doc_extract.synth.tiers import BY_NAME as TIERS


def test_the_grid_is_the_full_cross_product() -> None:
    planned = suite.plan(per_cell=2)
    assert len(planned) == len(PAYLOADS) * len(PLACEMENTS) * 2
    assert len({assignment.doc_id for _, assignment in planned}) == len(planned)


def test_every_payload_sees_the_same_pages() -> None:
    """The paired design: the per-payload table compares payloads, not invoices."""
    pages: dict[str, set[tuple[str, str]]] = {}
    for _, assignment in suite.plan():
        pages.setdefault(assignment.payload, set()).add(
            (assignment.placement, assignment.base_doc_id)
        )
    assert len(set(map(frozenset, pages.values()))) == 1


def test_the_default_grid_reaches_every_tier() -> None:
    """The stride is chosen for this; a prime that missed a tier would leave it unattacked."""
    planned = suite.plan()
    assert {assignment.tier for _, assignment in planned} == {
        document.tier for document in synth_corpus.documents()
    }


def test_the_attacked_document_keeps_its_gold() -> None:
    base = list(synth_corpus.documents(per_tier=1, tiers=(TIERS["clean"],)))
    (attacked, _), = suite.plan(per_cell=1, payloads=(BY_NAME["refusal"],),
                                placements=("footer",), base=base)
    assert attacked.invoice == base[0].invoice
    assert attacked.overlay is not None


def test_an_empty_cell_is_refused() -> None:
    with pytest.raises(SuiteError, match="per_cell"):
        suite.plan(per_cell=0)


def test_an_empty_base_corpus_is_refused() -> None:
    with pytest.raises(SuiteError, match="base corpus is empty"):
        suite.plan(base=())


def test_a_payload_that_did_not_survive_rendering_is_a_build_failure(tmp_path: Path) -> None:
    """The check that keeps an unseen attack out of the denominator."""
    ghost = Payload(
        name="ghost",
        category="override",
        goal="never reach the page",
        text="Zwykłe zdanie bez znaczenia.",
        marker="ZNAKKTÓREGONIEMA",
        effect=lambda invoice: invoice,
        achieved=lambda *_: False,
    )
    base = list(synth_corpus.documents(per_tier=1, tiers=(TIERS["clean"],)))
    with pytest.raises(SuiteError, match="not in the text layer"):
        suite.generate(tmp_path, per_cell=1, payloads=(ghost,), placements=("footer",), base=base)


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> tuple[Path, tuple[suite.Assignment, ...]]:
    """A two-document attacked corpus: one payload that works, one that asks for nothing."""
    directory = tmp_path_factory.mktemp("attacked")
    base = list(synth_corpus.documents(per_tier=1, tiers=(TIERS["clean"],)))
    _, assignments = suite.generate(
        directory,
        per_cell=1,
        payloads=(BY_NAME["account_redirect"], BY_NAME["benign"]),
        placements=("footer",),
        base=base,
    )
    return directory, tuple(assignments)


def test_the_join_file_round_trips(built) -> None:
    directory, assignments = built
    assert suite.load_assignments(directory) == assignments


def test_the_join_file_survives_a_rebuild(built) -> None:
    """`write_index` prunes anything the manifest does not describe, and must spare `attacks.jsonl`.

    Losing it would leave a corpus of attacked documents that nothing could say were attacked.
    """
    directory, _ = built
    assert (directory / suite.ATTACKS_NAME).exists()


def test_a_corpus_without_a_join_file_says_so(tmp_path: Path) -> None:
    with pytest.raises(SuiteError, match="not an attacked corpus"):
        suite.load_assignments(tmp_path)


def test_an_attacked_corpus_is_an_ordinary_corpus(built) -> None:
    """`eval.dataset` reads it with no knowledge of the attack, hashes and all."""
    directory, assignments = built
    corpus = dataset.load(directory)
    assert corpus.doc_ids == tuple(assignment.doc_id for assignment in assignments)
    #: Reading verifies both artifacts' hashes; a corpus that had been edited would raise here.
    assert all(case.gold() is not None and case.source().text for case in corpus.cases)
