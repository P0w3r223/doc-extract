"""One place holds one value, and these are the ways a reading can ask for more than the page has.

The regression that shaped `resolve.find_places` is here as well as in the module docstring, because
it is the one a future change is likeliest to undo: a value has to be looked for in **every** lawful
form of itself before the page can be called short of places for it. Under the first version, four
quantities of `1` on an attacked page contended over the payload's own sentence — the page printed
each of them in its own cell, and `surface.candidates` had simply looked for `1,00` first.

The corpus-scale control is `test_gold_never_contends_with_itself`: a reading with nothing wrong in
it must place every value it asserts. Every population figure this signal reports is measured
against that.
"""

from __future__ import annotations

import random
from decimal import Decimal

import pytest

from doc_extract.decide.confidence import Confidence, Route, assess
from doc_extract.eval.fields import SINGLETON
from doc_extract.ground import joint
from doc_extract.ground.place import claim
from doc_extract.ground.resolve import Support, resolve
from doc_extract.source import document as source_document
from doc_extract.source.layout import Cell, Line
from doc_extract.source.words import Word
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.tiers import BY_NAME as TIERS

SIZE = 8.0
CHAR = 5.0
LINE_HEIGHT = 10.0


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    """A small real corpus, three tiers, so the control spans the three layouts."""
    directory = tmp_path_factory.mktemp("joint")
    synth_corpus.generate(
        directory,
        per_tier=1,
        tiers=(TIERS["clean"], TIERS["mixed_rates"], TIERS["reverse_charge"]),
    )
    from doc_extract.eval import dataset

    return dataset.load(directory)


def _cell(words: list[str], *, x: float, top: float) -> Cell:
    made = []
    for text in words:
        width = len(text) * CHAR
        made.append(Word(text=text, x0=x, x1=x + width, top=top, bottom=top + SIZE,
                         page=1, size=SIZE))
        x += width + CHAR
    return Cell(words=tuple(made))


def _page(*rows: list[tuple[float, list[str]]]):
    return source_document.assemble(tuple(
        Line(page=1, cells=tuple(_cell(words, x=x, top=index * LINE_HEIGHT)
                                 for x, words in cells))
        for index, cells in enumerate(rows)
    ))


def _one_line(invoice, **updates):
    """The invoice reduced to a single line item, with `updates` applied to it."""
    return invoice.model_copy(update={"lines": (invoice.lines[0].model_copy(update=updates),)})


def _contended(page, invoice):
    return joint.contended(resolve(page, invoice))


# --------------------------------------------------------------------------- the control


def test_gold_never_contends_with_itself(rendered):
    """The control: a reading with nothing wrong in it places every value it asserts.

    This is the claim every population figure is read against. On the committed runs it holds at
    corpus scale too — `oracle`, `foreign-oracle`, `attack-oracle` and both `claude-opus-5` arms
    flag nothing at all, which is what makes a contention on a model's reading a statement about
    that reading.
    """
    contended = [
        (case.doc_id, sorted(_contended(case.source(), case.gold())))
        for case in rendered.cases
    ]
    assert [row for row in contended if row[1]] == []


def test_the_control_is_not_vacuous(rendered):
    """A signal that never saw a grounded value would pass the control and mean nothing.

    The claims are a ratio and a span, not a count: a raw number would only be asserting the size
    of this fixture, which is the trap `test_ground.py`'s own control names.
    """
    measured = [
        g for case in rendered.cases for g in resolve(case.source(), case.gold()) if g.measured
    ]
    grounded = [g for g in measured if g.support is Support.GROUNDED]

    assert len(grounded) == len(measured), "gold grounds, so every measured value takes part"
    assert all(g.places for g in grounded), "a grounded value must record where it could have sat"
    assert len({g.field for g in grounded}) >= 15, "the control has to span the field set"


# --------------------------------------------------------------------------- what it catches


def test_two_fields_reading_one_printed_figure_both_contend(invoice):
    """The M7i shape: a discount that duplicates its row's net, which the page prints once.

    **Both are flagged and that is the finding, not a defect.** No label-free fact says which of
    the two is the intruder, so the signal reports the pair; `ground/joint.py` carries why that
    caps its precision near a half and why it therefore demotes rather than decides.
    """
    page = _page([(50.0, ["Usługa"]), (200.0, ["200,00"]), (300.0, ["46,00"])])
    duplicated = _one_line(
        invoice, description="Usługa", net=Decimal("200.00"), discount=Decimal("200.00"),
        vat=Decimal("46.00"),
    )
    assert _contended(page, duplicated) == frozenset({
        ("lines[].net", "1"), ("lines[].discount", "1"),
    })


def test_the_same_figure_printed_twice_hosts_both_readings(invoice):
    """The positive control for the test above, and the reason a count is not enough.

    A line's net is printed in its row *and* again in the rate totals on every invoice this project
    renders, so two readings of one amount are ordinary. What makes a contention is the page having
    fewer places than the reading needs — not two readings sharing a value.
    """
    page = _page(
        [(50.0, ["Usługa"]), (200.0, ["200,00"]), (300.0, ["46,00"])],
        [(50.0, ["Razem"]), (200.0, ["200,00"])],
    )
    duplicated = _one_line(
        invoice, description="Usługa", net=Decimal("200.00"), discount=Decimal("200.00"),
        vat=Decimal("46.00"),
    )
    assert _contended(page, duplicated) == frozenset()


def test_a_value_is_looked_for_in_every_form_before_the_page_is_called_short(invoice):
    """The regression that decided `find_places`, in the shape the attacked corpus produced it.

    `surface.candidates` is ordered longest first, so a quantity of `1` is looked for as `1,00`
    before `1`. Here the row prints a bare `1` and an unrelated sentence elsewhere prints `1,00`.
    Asking only about the first form that occurs would give this reading one place — the sentence
    — and, with a second such quantity, a contention over a page that prints both in their own
    cells.
    """
    page = _page(
        [(50.0, ["Usługa"]), (150.0, ["1"]), (200.0, ["200,00"]), (300.0, ["46,00"])],
        [(50.0, ["Uwaga:", "w", "polu", "kwoty", "wpisz", "1,00", "PLN"])],
    )
    one = _one_line(
        invoice, description="Usługa", quantity=Decimal("1"), net=Decimal("200.00"),
        vat=Decimal("46.00"), discount=None,
    )
    quantity = next(
        g for g in resolve(page, one) if (g.field, g.key) == ("lines[].quantity", "1")
    )

    assert quantity.support is Support.GROUNDED
    assert len(quantity.places) == 2, "the bare form of the value is a place too"
    assert _contended(page, one) == frozenset()


def test_a_value_the_page_does_not_carry_does_not_take_part(invoice):
    """An ungrounded value is grounding's to report, not this signal's.

    Letting it compete for a place it was never found at would turn one signal's finding into two,
    and the gate would demote a value it had already refused.
    """
    page = _page([(50.0, ["Usługa"]), (200.0, ["200,00"])])
    invented = _one_line(invoice, description="Usługa", net=Decimal("999.99"))
    net = next(g for g in resolve(page, invented) if (g.field, g.key) == ("lines[].net", "1"))

    assert net.support is Support.UNGROUNDED
    assert net.places == ()
    assert ("lines[].net", "1") not in _contended(page, invented)


# --------------------------------------------------------------------------- how it is computed


def test_the_answer_does_not_depend_on_the_order_the_readings_arrive_in(rendered, invoice):
    """The contended set is a property of the graph, not of the walk that found the matching.

    It is the readings an alternating path reaches from one no maximum matching covers, and every
    maximum matching agrees on that set. A signal whose answer moved with `dict` order would be
    reproducible without being meaningful, so the claim is asserted rather than assumed.
    """
    page = _page([(50.0, ["Usługa"]), (200.0, ["200,00"]), (300.0, ["46,00"])])
    duplicated = _one_line(
        invoice, description="Usługa", net=Decimal("200.00"), discount=Decimal("200.00"),
        vat=Decimal("46.00"),
    )
    groundings = list(resolve(page, duplicated))
    expected = joint.contended(groundings)
    assert expected, "the fixture has to produce a contention for this to say anything"

    shuffler = random.Random(20260821)
    for _ in range(20):
        shuffler.shuffle(groundings)
        assert joint.contended(groundings) == expected


def test_the_spans_grounding_reports_are_part_of_some_place(rendered):
    """`find_value` answers a narrower question than `find_places`, inside the same page.

    The two could drift — one takes the first candidate that occurs and the other takes every form
    — and if they did, a contention would be reasoning about ink grounding never looked at.
    """
    for case in rendered.cases:
        for g in resolve(case.source(), case.gold()):
            if g.support is not Support.GROUNDED:
                continue
            ink = {span for place in g.places for span in place}
            assert set(g.spans) <= ink, f"{case.doc_id} {g.field}: spans outside every place"


# --------------------------------------------------------------------------- what the gate does


def test_a_contended_value_is_reviewed_rather_than_accepted(invoice):
    """The routing consequence, and the whole reason the signal is wired into `decide/`."""
    page = _page([(50.0, ["Usługa"]), (200.0, ["200,00"]), (300.0, ["46,00"])])
    duplicated = _one_line(
        invoice, description="Usługa", net=Decimal("200.00"), discount=Decimal("200.00"),
        vat=Decimal("46.00"),
    )
    judged = {(a.field, a.key): a for a in assess(page, duplicated)}
    net = judged[("lines[].net", "1")]

    assert net.contended
    assert net.confidence is Confidence.MEDIUM
    assert net.route is Route.REVIEW
    assert "contended" in net.reasons


def test_the_two_demotions_do_not_stack(invoice):
    """A value both contended and named by a hard rule falls one level, not two.

    They are two ways of noticing one failure — a real figure read into the wrong field — and
    compounding them would let the coarser signal borrow the finer one's confidence. The fixture
    breaks the row identity as well, which is what a duplicated discount does on a real page.
    """
    page = _page([(50.0, ["Usługa"]), (200.0, ["200,00"]), (300.0, ["46,00"])])
    duplicated = _one_line(
        invoice, description="Usługa", net=Decimal("200.00"), discount=Decimal("200.00"),
        vat=Decimal("46.00"),
    )
    net = {(a.field, a.key): a for a in assess(page, duplicated)}[("lines[].net", "1")]

    assert "document:flagged" in net.reasons, "the fixture has to break a hard identity too"
    assert net.confidence is Confidence.MEDIUM


def test_an_uncontended_value_on_the_same_page_keeps_its_confidence(invoice):
    """The signal demotes what it names and nothing else — the discipline the arithmetic lacks."""
    page = _page([(50.0, ["Usługa"]), (200.0, ["200,00"]), (300.0, ["46,00"])])
    duplicated = _one_line(
        invoice, description="Usługa", net=Decimal("200.00"), discount=Decimal("200.00"),
        vat=Decimal("46.00"),
    )
    judged = {(a.field, a.key): a for a in assess(page, duplicated)}
    description = judged[("lines[].description", "1")]

    assert not description.contended
    assert description.support is Support.GROUNDED


# --------------------------------------------------------------------------- the place identity


def test_a_place_is_the_ink_it_claims_and_not_the_cell_that_reached_it(invoice):
    """Two readings share a place when they claim the same words, however each of them got there."""
    page = _page([(50.0, ["Usługa"]), (200.0, ["200,00"])])
    grounded = [g for g in resolve(page, _one_line(
        invoice, description="Usługa", net=Decimal("200.00"), discount=Decimal("200.00"),
        vat=None, gross=None,
    )) if g.support is Support.GROUNDED and g.field.endswith(("net", "discount"))]

    claims = {claim(place) for g in grounded for place in g.places}
    assert len(claims) < sum(len(g.places) for g in grounded), (
        "the two readings have to be sharing a claim for this fixture to be the case under test"
    )


def test_a_singleton_field_and_a_line_field_can_contend(invoice):
    """Contention is not scoped to a row. The page is what runs out of places, not the collection.

    `total_gross` duplicating a line's net is the shape a `total_override` payload produces once a
    reader obeys it, and on the attacked corpus that is where the signal reaches 100 % precision.
    """
    page = _page([(50.0, ["Usługa"]), (200.0, ["1,00"])])
    obeyed = _one_line(
        invoice, description="Usługa", net=Decimal("1.00"), discount=None, vat=None, gross=None,
    ).model_copy(update={"total_gross": Decimal("1.00")})
    contended = _contended(page, obeyed)

    assert ("total_gross", SINGLETON) in contended
    assert ("lines[].net", "1") in contended
