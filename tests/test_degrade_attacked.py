"""M6's grid crossed with M7's rungs, and the one number that composition exists to produce.

Three things have to hold for the corpus to be a measurement rather than 168 pictures:

* **The cross is full and the pairing survives it.** Every payload meets every placement meets every
  rung, on the same base invoices, or a per-rung difference is a difference between documents.
* **The gold does not move.** Neither an injected sentence nor a scanner changes what the invoice
  states, so `eval` reads this corpus with no knowledge that either happened.
* **`reach` says which channel carried the payload, and it is not vacuous in either direction.**
  Ink reaches the image at every rung; white ink reaches nobody at any of them. A version that
  answered "no" everywhere would pass a test that only looked for the white-ink result.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doc_extract.attack.payloads import BY_NAME, PAYLOADS, Payload
from doc_extract.attack.suite import SuiteError
from doc_extract.degrade import attacked
from doc_extract.degrade.rungs import BY_NAME as RUNGS
from doc_extract.degrade.rungs import RUNGS as ALL_RUNGS
from doc_extract.eval import dataset
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.overlay import FOOTER, INVISIBLE, PLACEMENTS
from doc_extract.synth.tiers import BY_NAME as TIERS

#: Nine documents: coprime with the suite's stride of 41, and enough for four placement slots.
BASE_TIERS = ("clean", "advance", "correction")


def _base():
    return [
        document
        for name in BASE_TIERS
        for document in synth_corpus.documents(per_tier=3, tiers=(TIERS[name],))
    ]


# --------------------------------------------------------------------------- the plan, pure


def test_the_cross_is_full() -> None:
    planned = attacked.plan(per_cell=2, base=_base())

    assert len(planned) == len(PAYLOADS) * len(PLACEMENTS) * 2 * len(ALL_RUNGS)
    assert len({assignment.doc_id for _, _, assignment in planned}) == len(planned)


def test_every_cell_of_the_cross_is_filled_equally() -> None:
    """A rung that appeared under six payloads and not the seventh would not be a factor."""
    cells: dict[tuple[str, str, str], int] = {}
    for _, rung, assignment in attacked.plan(per_cell=2, base=_base()):
        key = (assignment.payload, assignment.placement, rung.name)
        cells[key] = cells.get(key, 0) + 1

    assert len(cells) == len(PAYLOADS) * len(PLACEMENTS) * len(ALL_RUNGS)
    assert set(cells.values()) == {2}


def test_the_same_invoice_appears_at_every_rung() -> None:
    """What makes the per-rung comparison paired: only the picture changes."""
    by_rung: dict[str, set[tuple[str, str, str]]] = {}
    for _, rung, assignment in attacked.plan(per_cell=1, base=_base()):
        by_rung.setdefault(rung.name, set()).add(
            (assignment.payload, assignment.placement, assignment.base_doc_id)
        )

    assert len(set(map(frozenset, by_rung.values()))) == 1


def test_the_template_column_is_the_rung_and_the_layout_is_kept_on_the_document() -> None:
    """The manifest has one column for what a page looks like; this corpus varies the scanner."""
    for document, rung, assignment in attacked.plan(per_cell=1, base=_base()):
        assert assignment.template == rung.name
        assert document.template not in RUNGS, "the page would be printed in a layout called a rung"


def test_a_scanned_attacked_document_keeps_its_gold() -> None:
    base = _base()
    planned = attacked.plan(
        per_cell=1, payloads=(BY_NAME["refusal"],), placements=(FOOTER,), base=base,
    )
    golds = {document.invoice for document, _, _ in planned}

    assert len(golds) == 1
    assert golds.pop() == base[0].invoice


def test_a_corpus_with_no_scanner_is_refused() -> None:
    with pytest.raises(SuiteError, match="no rungs"):
        attacked.plan(rungs=(), base=_base())


# --------------------------------------------------------------------------- the corpus, built


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> tuple[Path, tuple[attacked.Reach, ...]]:
    """One payload in two placements at all three rungs: ink, and the same words in white."""
    directory = tmp_path_factory.mktemp("attacked-scanned")
    _, _, reaches = attacked.generate(
        directory,
        per_cell=1,
        payloads=(BY_NAME["account_redirect"],),
        placements=(FOOTER, INVISIBLE),
        base=_base(),
    )
    return directory, tuple(reaches)


def _by_placement(reaches, placement: str) -> list[attacked.Reach]:
    return [row for row in reaches if row.placement == placement]


def test_ink_reaches_the_image_at_every_rung(built) -> None:
    _, reaches = built
    printed = _by_placement(reaches, FOOTER)

    assert len(printed) == len(ALL_RUNGS)
    assert all(row.on_the_image for row in printed)


def test_ink_reaches_the_text_layer_only_where_one_survives(built) -> None:
    _, reaches = built

    assert {row.rung for row in _by_placement(reaches, FOOTER) if row.in_text_layer} == {
        rung.name for rung in ALL_RUNGS if rung.text_layer
    }


def test_white_ink_reaches_nobody_at_any_rung(built) -> None:
    """The finding: a scan erases the attack that was designed to be invisible to a human.

    On the `searchable` rung it is the recogniser that erases it — there is no pixel to recognise —
    and on the other two the whole text layer is gone. Same answer, two different reasons.
    """
    _, reaches = built
    hidden = _by_placement(reaches, INVISIBLE)

    assert len(hidden) == len(ALL_RUNGS)
    assert all(row.reaches_nobody for row in hidden)


def test_a_payload_that_never_reached_the_printed_page_is_a_build_failure(tmp_path: Path) -> None:
    """M6's guarantee, kept where it still means what it meant: before the scanner, not after."""
    ghost = Payload(
        name="ghost",
        category="override",
        goal="never reach the page",
        text="Zwykłe zdanie bez znaczenia.",
        marker="ZNAKKTÓREGONIEMA",
        effect=lambda invoice: invoice,
        achieved=lambda *_: False,
    )
    with pytest.raises(SuiteError, match="as printed"):
        attacked.generate(
            tmp_path, per_cell=1, payloads=(ghost,), placements=(FOOTER,),
            rungs=(RUNGS["rasterised"],), base=_base(),
        )


def test_the_reach_file_round_trips(built) -> None:
    directory, reaches = built
    assert attacked.load_reaches(directory) == reaches


def test_a_corpus_without_a_reach_file_says_so(tmp_path: Path) -> None:
    with pytest.raises(SuiteError, match="not a scanned attacked corpus"):
        attacked.load_reaches(tmp_path)


def test_a_scanned_attacked_corpus_is_an_ordinary_corpus(built) -> None:
    """`eval.dataset` reads it with no knowledge of either the attack or the scanner."""
    directory, reaches = built
    corpus = dataset.load(directory)

    assert corpus.doc_ids == tuple(row.doc_id for row in reaches)
    assert all(case.gold() is not None for case in corpus.cases)


def test_the_manifest_says_the_rung_and_the_provenance_remembers_the_layout(built) -> None:
    directory, _ = built
    corpus = dataset.load(directory)

    assert {case.template for case in corpus.cases} == {rung.name for rung in ALL_RUNGS}
    layouts = corpus.provenance["layouts"]
    assert set(layouts) == set(corpus.doc_ids)
    assert not set(layouts.values()) & set(RUNGS)
