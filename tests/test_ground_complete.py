"""The page kept printing and the reading stopped — and the two shapes that must not fire.

`ground/complete.py` exists for a population `place.py` measured and could not touch: 273 of
`pattern`'s 292 wrong values still ground, and the dominant failure is a description that stops
early. The two bounds it rests on were each measured against a control it alone clears, and each has
a test here on a page laid out by hand, so what is under test is the geometry rather than a property
of `synth/render.py`:

* **the line below must be narrower than the row** — removing it alone costs the control 72 gold
  values on `data/synthetic`, and removing both leaves *is there anything below this value in its
  column*, which fires on 1169 of 1238;
* **the value's last cell must have something to its left** — removing it alone costs nothing on
  four corpora and 72 gold values on `data/foreign`, whose `statement` dialect prints a party as a
  name beside a label with its address underneath.

The control that gold is never cut short against its own page lives **here**, in
`test_gold_is_never_cut_short_against_its_own_page`, on a corpus this module renders. It is
deliberately not folded into `test_ground.py`'s grounding control: that fixture is sized for a
different question and would pass against the `ground/place.py` defect this one has to fail
against — see `PER_TIER`.

Its reach is a dozen documents, not the 4847 gold text values of the five committed corpora. That
wider sweep is a one-off measurement recorded in `docs/adr/0002_placement.md`, not something CI
re-derives, because it needs corpora that are not committed.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from doc_extract.decide.confidence import Confidence, Route, assess
from doc_extract.eval import dataset
from doc_extract.eval.fields import SINGLETON
from doc_extract.ground.complete import Frame, cut_short
from doc_extract.ground.resolve import Support, resolve
from doc_extract.schema.ksef import RateTotal
from doc_extract.source import document as source_document
from doc_extract.source.layout import Cell, Line
from doc_extract.source.words import Word
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.tiers import BY_NAME as TIERS

SIZE = 8.0
CHAR = 5.0
LINE_HEIGHT = 10.0


def _cell(words: list[str], *, x: float, top: float) -> Cell:
    made = []
    for text in words:
        width = len(text) * CHAR
        made.append(Word(text=text, x0=x, x1=x + width, top=top, bottom=top + SIZE,
                         page=1, size=SIZE))
        x += width + CHAR
    return Cell(words=tuple(made))


def _page(*rows: list[tuple[float, list[str]]]):
    """A document from cells at explicit horizontal positions, one row per printed line."""
    return source_document.assemble(tuple(
        Line(page=1, cells=tuple(_cell(words, x=x, top=index * LINE_HEIGHT)
                                 for x, words in cells))
        for index, cells in enumerate(rows)
    ))


def _described(invoice, description: str):
    """The invoice reduced to one line item carrying `description`.

    Dropping two of the fixture's three lines leaves the rate totals stating more than the items
    do, so a hard rule fires and names `lines[].description` — which is exactly what
    `test_a_cut_short_value_lands_at_low_however_many_other_signals_agree` needs and exactly what
    `_coherent` exists to avoid.
    """
    return invoice.model_copy(update={
        "lines": (invoice.lines[0].model_copy(update={"description": description}),),
    })


def _coherent(invoice, description: str):
    """One line item carrying `description`, with the totals rebuilt so every invariant holds.

    23 % of 200.00 is 46.00 and the gross is 246.00, computed here rather than borrowed from
    `conftest`: a fixture whose arithmetic came from the code under test would prove nothing.
    """
    line = invoice.lines[0].model_copy(update={
        "description": description, "quantity": Decimal("2"),
        "unit_price_net": Decimal("100.00"), "discount": None,
        "net": Decimal("200.00"), "vat": Decimal("46.00"), "vat_rate": "23",
    })
    return invoice.model_copy(update={
        "lines": (line,),
        "rate_totals": (RateTotal(rate="23", net=Decimal("200.00"), vat=Decimal("46.00")),),
        "total_gross": Decimal("246.00"),
    })


def _cut(page, invoice) -> bool:
    """Whether the line item's description is reported cut short on this page."""
    return ("lines[].description", "1") in cut_short(page, resolve(page, invoice))


#: A table row: an ordinal, the description column, then two amount columns. The description
#: column's `x` is shared by every continuation below, which is what makes it a column.
_ORDINAL = 10.0
_DESCRIPTION = 60.0
_AMOUNTS = (300.0, 380.0)


def _row(description: list[str], *, ordinal: str = "1") -> list[tuple[float, list[str]]]:
    return [
        (_ORDINAL, [ordinal]),
        (_DESCRIPTION, description),
        (_AMOUNTS[0], ["100,00"]),
        (_AMOUNTS[1], ["123,00"]),
    ]


def _wrap(words: list[str]) -> list[tuple[float, list[str]]]:
    return [(_DESCRIPTION, words)]


# --------------------------------------------------------------------------- the control


#: Documents per tier in the corpus control below. **Measured, not chosen for roundness.** The
#: control's job is to fail against the multiset placement `ground/place.py` replaced, and the
#: shape it has to contain is a description wrapped over *three* lines — which the `reverse_charge`
#: tier only produces from its fourth seed on. At 1, 2 and 3 per tier the multiset placement passes
#: this control; at 4 it fails on 2 gold values and at 5 on 5. A fixture that could not fail is a
#: fixture that asserts the size of itself.
PER_TIER = 4


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    """A small real corpus. `reverse_charge` is not decoration — it is the tier whose descriptions
    wrap over three lines, which is the shape that made both this module and the ordering fix in
    `ground/place.py` necessary."""
    directory = tmp_path_factory.mktemp("complete")
    synth_corpus.generate(
        directory,
        per_tier=PER_TIER,
        tiers=(TIERS["clean"], TIERS["mixed_rates"], TIERS["reverse_charge"]),
    )
    return dataset.load(directory)


def test_gold_is_never_cut_short_against_its_own_page(rendered):
    """The control, and the one that decided the rule's two bounds.

    A value the renderer drew whole cannot be a value the page carries more of. Both bounds were
    fixed by breaking this: removing the narrower-line test costs 72 gold values on
    `data/synthetic`, removing the flank test costs 72 on `data/foreign`, and removing both leaves a
    rule that fires on 1169 of 1238.

    **It also guards `ground/place.py`'s ordering, and this fixture is sized so that it can.**
    Against the multiset placement the check fires on 15 gold values of the full `data/synthetic`,
    every one a three-line description that had finished itself on the row above — but those
    documents start at the fourth seed of the `reverse_charge` tier, so a smaller fixture would pass
    against the defect it names. At `PER_TIER` it fails on **2**. The two hand-built regressions in
    `tests/test_ground_place.py` pin the same defect without needing a corpus at all.
    """
    flagged = [
        (case.doc_id, field, key)
        for case in rendered.cases
        for field, key in cut_short(case.source(), resolve(case.source(), case.gold()))
    ]
    assert flagged == []


def test_the_control_has_something_to_catch(rendered):
    """A corpus with no wrapped value at all would pass the control and mean nothing.

    The claim is that the fixture prints descriptions across more than one line, which is the only
    shape this rule can fire on — asserted through the places grounding recorded rather than
    through the renderer, so it stays a statement about the page.
    """
    wrapped = [
        grounding
        for case in rendered.cases
        for grounding in resolve(case.source(), case.gold())
        if grounding.field == "lines[].description"
        and grounding.support is Support.GROUNDED
        and len({round(span.top) for span in grounding.spans}) > 1
    ]
    assert len(wrapped) >= 3, "the fixture has to carry descriptions the renderer wrapped"


# --------------------------------------------------------------------------- what it catches


def test_a_description_that_stops_at_the_end_of_its_first_line_is_cut_short(invoice):
    """The population this module was built for: one whole cell of a two-cell wrapped run.

    Nothing about the cell itself is unclaimed — the reader took all of it — which is why the
    natural check `did the value claim its cell` is blind here and 100 % of `pattern`'s wrong
    descriptions look complete to it.
    """
    page = _page(_row(["Roboty", "budowlane"]), _wrap(["konstrukcja", "stalowa"]))
    grounded = {(g.field, g.key): g for g in resolve(page, _described(invoice, "Roboty budowlane"))}
    assert grounded[("lines[].description", "1")].support is Support.GROUNDED
    assert _cut(page, _described(invoice, "Roboty budowlane"))


def test_the_whole_wrapped_description_is_not_cut_short(invoice):
    """The other half of the same page: read it all and the rule is silent."""
    page = _page(_row(["Roboty", "budowlane"]), _wrap(["konstrukcja", "stalowa"]))
    assert not _cut(page, _described(invoice, "Roboty budowlane konstrukcja stalowa"))


def test_a_reading_that_stopped_on_a_wrap_line_is_not_seen(invoice):
    """The rule's limit, asserted so it cannot be lost by accident.

    The reading took the row and one wrap line of three, so the page carries more of the value and
    this is a truncation. It is invisible here, because the flank question is asked of the value's
    *last* cell and a wrap line has nothing to its left. Asking it of the value's row instead would
    see it — and costs 133 gold values on `data/synthetic` alone, for not one extra catch on any
    run; `ground/complete.py` carries the sweep and the mechanism.
    """
    page = _page(
        _row(["Roboty", "budowlane"]),
        _wrap(["konstrukcja", "stalowa"]),
        _wrap(["hali", "magazynowej"]),
    )
    assert not _cut(page, _described(invoice, "Roboty budowlane konstrukcja stalowa"))


# --------------------------------------------------------------------------- the two bounds


def test_the_next_row_of_the_table_is_not_a_continuation(invoice):
    """The bound that carries the whole idea: a new row prints every column, a wrap prints one.

    Removing it on its own costs the control **72** gold values on `data/synthetic`; removing it
    *and* the left-flank bound leaves *is there anything below this value in its column*, which
    fires on 1169 of the corpus's 1238 gold text values. The two figures answer different
    questions, and the module docstring reports the single-bound one beside the flank bound's so
    they can be compared.
    """
    page = _page(_row(["Roboty", "budowlane"]), _row(["Dostawa", "złomu"], ordinal="2"))
    assert not _cut(page, _described(invoice, "Roboty budowlane"))


def test_a_left_aligned_block_does_not_wrap_into_its_next_field(invoice):
    """`data/foreign`'s `statement` dialect, and the 72 gold values that measured this bound.

    A party is printed as its name beside a right-hand label, with its address on the line below.
    The address line is narrower than the name line and is not a continuation of anything: the name
    is at the head of a **block**, not inside a table row. Nothing is printed to its left, and that
    is what the rule asks.
    """
    page = _page(
        [(_ORDINAL, ["Hurtownia", "Spożywcza"]), (_AMOUNTS[1], ["Sprzedający"])],
        [(_ORDINAL, ["ul.", "Krakowska", "61"])],
    )
    seller = invoice.model_copy(update={
        "seller": invoice.seller.model_copy(update={"name": "Hurtownia Spożywcza"}),
    })
    #: `SINGLETON`, not a literal: a field with one instance is keyed by the empty string, and an
    #: assertion naming any other key would be about a tuple that cannot occur — vacuously true
    #: whether or not the bound it guards exists. That is exactly how this test first shipped.
    assert ("seller.name", SINGLETON) not in cut_short(page, resolve(page, seller))


def test_a_label_on_the_right_alone_does_not_make_a_block_a_table(invoice):
    """The bound is the **left** side, and this is the page that says the right would not do.

    The shape above has a cell to the right of the value and is still a block. A rule asking about
    the right-hand side would fire on it, which is why the module asks about the left and says so.
    """
    page = _page(
        [(_ORDINAL, ["Hurtownia", "Spożywcza"]), (_AMOUNTS[1], ["Sprzedający"])],
        [(_ORDINAL, ["ul.", "Krakowska", "61"])],
    )
    frame = Frame.of(page)
    name_cell = next(i for i, cell in enumerate(page.cells)
                     if page.text_of(cell) == "Hurtownia Spożywcza")
    assert not frame._flanked(name_cell)


# --------------------------------------------------------------------------- what it declines


def test_a_value_the_page_does_not_carry_is_left_to_grounding(invoice):
    """An `UNGROUNDED` value has no place, so there is nothing to ask whether the page continues.

    Kept out here rather than answered `False` by accident: two signals reporting one failure would
    make `completeness` look like it had caught something grounding had already named.
    """
    page = _page(_row(["Roboty", "budowlane"]), _wrap(["konstrukcja", "stalowa"]))
    invented = _described(invoice, "Wynajem powierzchni biurowej")
    grounded = {(g.field, g.key): g for g in resolve(page, invented)}
    assert grounded[("lines[].description", "1")].support is Support.UNGROUNDED
    assert not _cut(page, invented)


def test_an_amount_is_not_asked_about(invoice):
    """A non-text value's spans are every occurrence of it, not a place, so the question is wrong.

    **The page has to make the amount fireable, or the test passes for the wrong reason.** The
    narrower line below carries a left-hand cell as well as one under the amount column, so the
    amount's own cell is flanked and the line beneath it is narrower than its row — every condition
    `continues` asks for. What stops the rule is only the `Match.TEXT` guard in `_asked`, which is
    the guard this test is named for; an earlier version put the continuation alone on its line, so
    the flank bound blocked it first and removing the guard changed nothing.
    """
    page = _page(
        _row(["Roboty", "budowlane"]),
        [(_ORDINAL, ["ciąg"]), (_AMOUNTS[0], ["100,00"])],
        [(_AMOUNTS[0], ["dalej"])],
    )
    priced = invoice.model_copy(update={
        "lines": (invoice.lines[0].model_copy(update={
            "description": "Roboty budowlane", "net": Decimal("100.00"),
        }),),
    })
    flagged = cut_short(page, resolve(page, priced))
    assert ("lines[].net", "1") not in flagged


# --------------------------------------------------------------------------- what the gate does


def test_a_cut_short_value_is_reviewed_rather_than_accepted(invoice):
    """The routing consequence, and the whole reason the signal is wired into `decide/`.

    `LOW` rather than one step down from `HIGH`: the claim is the one `Support.PARTIAL` makes, that
    the reading took part of a printed value. On `pattern` this rule is what takes the
    auto-accepted bucket from 54 leaked values to none.
    """
    page = _page(_row(["Roboty", "budowlane"]), _wrap(["konstrukcja", "stalowa"]))
    judged = {(a.field, a.key): a for a in assess(page, _described(invoice, "Roboty budowlane"))}
    description = judged[("lines[].description", "1")]

    assert description.cut_short
    assert description.support is Support.GROUNDED, "grounding is what cannot see this"
    assert description.confidence is Confidence.LOW
    assert description.route is Route.REVIEW
    assert "cut_short" in description.reasons


def test_a_cut_short_value_lands_at_low_however_many_other_signals_agree(invoice):
    """The documented precedence: the strongest signal decides, not the order of the code.

    A hard rule naming the same field would demote it to `MEDIUM` on its own, so the precondition is
    asserted rather than assumed — without it the test would pass while accusing nothing, and could
    not see the precedence it exists for. Both reason tokens are required for the reason `_assess`
    records them all: a token that vanished whenever a second signal agreed would make one signal
    look silent in a report.
    """
    page = _page(_row(["Roboty", "budowlane"]), _wrap(["konstrukcja", "stalowa"]))
    judged = {(a.field, a.key): a for a in assess(page, _described(invoice, "Roboty budowlane"))}
    description = judged[("lines[].description", "1")]

    assert description.cut_short, "the fixture has to produce a truncation on this field"
    assert "rule:lines[].description" in description.reasons, "and a hard rule has to name it too"
    assert description.confidence is Confidence.LOW, "not MEDIUM, which the rule alone would give"
    assert "cut_short" in description.reasons


def test_a_complete_value_on_the_same_page_keeps_its_confidence(invoice):
    """The signal demotes what it names and nothing else — the discipline the arithmetic lacks.

    Read against the test above: same page, same field, and the only difference is that the reading
    took the whole of the value. It needs an arithmetically coherent invoice, because a hard rule
    would otherwise demote the field for reasons that have nothing to do with this signal — which
    is asserted, so the test cannot quietly stop being about `HIGH`.
    """
    page = _page(_row(["Roboty", "budowlane"]), _wrap(["konstrukcja", "stalowa"]))
    whole = _coherent(invoice, "Roboty budowlane konstrukcja stalowa")
    description = {(a.field, a.key): a for a in assess(page, whole)}[("lines[].description", "1")]

    assert not description.cut_short
    assert "document:flagged" not in description.reasons, "the fixture has to break no hard rule"
    assert description.confidence is Confidence.HIGH
    assert description.route is Route.ACCEPT


# --------------------------------------------------------------------------- the frame itself


def test_a_line_is_read_out_of_the_separators_the_document_already_wrote():
    """`Frame` derives lines from the text rather than re-deriving them from the boxes.

    Asserted directly because the alternative — a second implementation of `layout.group_lines` —
    is the failure mode the class exists to avoid, and it would be invisible in every rule above.
    """
    page = _page(_row(["Roboty", "budowlane"]), _wrap(["konstrukcja"]))
    frame = Frame.of(page)
    assert [len(line) for line in frame.lines] == [4, 1]
    assert frame.line_of[0] == 0 and frame.line_of[-1] == 1
