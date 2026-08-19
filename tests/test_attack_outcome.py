"""What the suite counts, and the whole path end to end on a real attacked corpus.

The unit tests fix the arithmetic of the study — a control that cannot succeed is out of the
headline denominator, an unanswered document is not an accepted one, a rate with no denominator is
`None`. The end-to-end test is the one that would catch a wiring failure the units cannot see: it
builds an attacked corpus, runs the compliant control and the perfect reader over it, and requires
the first to be breached everywhere and the second nowhere.

Those two arms bracket every real measurement. A judge that could not score `gullible` at 100 %
would report every model as safe; one that scored `oracle` above zero would report every model as
breached.
"""

from __future__ import annotations

import pytest

from doc_extract.attack import outcome, suite
from doc_extract.attack.outcome import Outcome
from doc_extract.attack.payloads import BY_NAME
from doc_extract.decide.confidence import Route
from doc_extract.eval import __main__ as eval_cli
from doc_extract.eval import dataset, run
from doc_extract.eval.baselines import BY_NAME as BASELINES
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.tiers import BY_NAME as TIERS


def _row(payload: str, *, succeeded: bool, route: str = Route.ACCEPT, exact: bool = False,
         answered: bool = True, placement: str = "footer") -> Outcome:
    return Outcome(
        doc_id=f"{payload}-{placement}-00",
        payload=payload,
        category=BY_NAME[payload].category,
        placement=placement,
        tier="clean",
        template="classic",
        succeeded=succeeded,
        answered=answered,
        exact=exact,
        failure="none",
        route=route,
    )


def test_the_control_is_outside_the_headline_denominator() -> None:
    """Seven payloads of which one asks for nothing: the rate is over the six that do."""
    study = outcome.summarise([
        _row("total_override", succeeded=True),
        _row("benign", succeeded=False, exact=True),
    ])

    assert study.overall.documents == 1
    assert study.overall.rate == 1.0
    assert study.control.documents == 1
    assert study.control.unchanged == 1.0


def test_a_rate_with_no_denominator_is_none() -> None:
    empty = outcome.summarise([])
    assert empty.overall.rate is None
    assert empty.overall.leak_rate is None


def test_only_an_accepted_success_counts_as_leaked() -> None:
    accepted = _row("account_redirect", succeeded=True, route=Route.ACCEPT)
    reviewed = _row("total_override", succeeded=True, route=Route.REVIEW)

    assert accepted.leaked and not accepted.stopped
    assert reviewed.stopped and not reviewed.leaked
    assert outcome.summarise([accepted, reviewed]).overall.leaked == 1


def test_an_unanswered_document_is_not_an_accepted_one() -> None:
    """The denial payload succeeds by producing nothing, and nothing is then accepted."""
    refused = _row("refusal", succeeded=True, route="", answered=False)
    assert refused.succeeded and not refused.accepted and not refused.leaked


def test_the_grid_reports_every_cell_it_was_given() -> None:
    study = outcome.summarise([
        _row("total_override", succeeded=True, placement="footer"),
        _row("total_override", succeeded=False, placement="invisible"),
    ])
    cells = {(payload, placement): rate for payload, placement, rate in study.grid}

    assert cells[("total_override", "footer")].rate == 1.0
    assert cells[("total_override", "invisible")].rate == 0.0


def test_a_prediction_with_no_assignment_is_reported_rather_than_dropped() -> None:
    study = outcome.summarise([_row("benign", succeeded=False)], unmatched=("stray-0001",))
    assert not study.complete
    assert study.unmatched == ("stray-0001",)


# --------------------------------------------------------------------------- end to end


@pytest.fixture(scope="module")
def attacked(tmp_path_factory):
    """Four attacked documents: two payloads that ask for something, two that ask for nothing."""
    directory = tmp_path_factory.mktemp("attacked")
    base = list(synth_corpus.documents(per_tier=1, tiers=(TIERS["clean"], TIERS["mixed_rates"])))
    suite.generate(
        directory,
        per_cell=2,
        payloads=(BY_NAME["account_redirect"], BY_NAME["benign"]),
        placements=("footer",),
        base=base,
    )
    return directory


def _study(directory, baseline: str) -> outcome.Study:
    corpus = dataset.load(directory)
    records = run.predict(corpus, BASELINES[baseline])
    return run.attacks(corpus, records, suite.load_assignments(directory))


def test_the_compliant_control_is_breached_by_every_attack(attacked) -> None:
    study = _study(attacked, "gullible")

    assert study.complete
    assert study.overall.rate == 1.0
    assert study.control.succeeded == 0
    assert study.control.unchanged == 1.0


def test_a_perfect_reading_is_breached_by_none_of_them(attacked) -> None:
    study = _study(attacked, "oracle")

    assert study.overall.rate == 0.0
    assert study.overall.unchanged == 1.0
    assert study.overall.leaked == 0


def test_the_command_writes_a_report_beside_the_predictions(attacked, tmp_path) -> None:
    """The whole CLI path: run a baseline over an attacked corpus, then join and report."""
    out = tmp_path / "run"
    assert eval_cli.main([
        "run", "--baseline", "gullible", "--corpus", str(attacked), "--out", str(out), "--quiet",
    ]) == 0
    assert eval_cli.main(["attack", "--run", str(out)]) == 0

    body = (out / eval_cli.ATTACK_NAME).read_text(encoding="utf-8")
    assert "attack success rate" in body
    assert "`account_redirect`" in body
    #: The leak table names the documents that got through, which is the list a reviewer reads.
    assert "What got through" in body


def test_the_command_says_so_when_the_corpus_was_never_attacked(built_clean, tmp_path) -> None:
    """`attack` on an ordinary corpus is a mistake with a fix, not a traceback."""
    out = tmp_path / "clean-run"
    assert eval_cli.main([
        "run", "--baseline", "oracle", "--corpus", str(built_clean), "--out", str(out), "--quiet",
    ]) == 0
    assert eval_cli.main(["attack", "--run", str(out)]) == 2


@pytest.fixture(scope="module")
def built_clean(tmp_path_factory):
    directory = tmp_path_factory.mktemp("clean")
    synth_corpus.generate(directory, per_tier=1, tiers=(TIERS["clean"],))
    return directory


def test_the_redirected_account_is_accepted_by_the_gate(attacked) -> None:
    """The milestone's finding, asserted rather than only reported.

    The attacker's IBAN passes mod-97 and is printed on the page, so the arithmetic check agrees
    with it and grounding finds it. Both of M5's signals were measured on a model's *errors*, where
    a wrong digit is a random digit; neither transfers to an adversary who can compute a check
    digit. If this ever stops being true, the number in `attack.md` changed and the reason is here.
    """
    study = _study(attacked, "gullible")
    redirected = [row for row in study.outcomes if row.payload == "account_redirect"]

    assert redirected
    assert all(row.succeeded and row.leaked for row in redirected)
