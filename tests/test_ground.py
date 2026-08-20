"""Grounding has one control, and everything else here defends it.

**The control: gold, against the page it was rendered from, must ground completely.** It is the same
check `oracle` is to the detector — if a perfect reading does not resolve to the page, the layer is
broken and every suspicion it raises later is noise. That test caught the first version of this
module failing on 14.9 % of gold fields, so it is not ceremony.

The rest are the specific ways a substring search can lie: matching inside a longer number, matching
a value that is really the company's legal form, or crediting a word to a page that only prints it
once when the value claims it twice.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from doc_extract.ground import surface
from doc_extract.ground.resolve import NOT_PRINTED, Support, resolve
from doc_extract.source import document as source_document
from doc_extract.source.layout import Cell, Line
from doc_extract.source.words import Word
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.tiers import BY_NAME as TIERS


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    """A small real corpus: gold invoices and the PDFs they were rendered into.

    Three tiers rather than one, because the layouts differ in how much of a row lands in a single
    cell, and the substring search exists precisely for the one that prints a row as prose.
    """
    directory = tmp_path_factory.mktemp("ground")
    synth_corpus.generate(
        directory,
        per_tier=1,
        tiers=(TIERS["clean"], TIERS["mixed_rates"], TIERS["reverse_charge"]),
    )
    from doc_extract.eval import dataset

    return dataset.load(directory)


def _page(*lines: list[list[str]]):
    """A document from words laid out by hand, for the cases a rendered corpus cannot produce."""
    built = []
    for row, cells in enumerate(lines):
        made = []
        x = 0.0
        for words in cells:
            spans = []
            for text in words:
                spans.append(Word(text=text, x0=x, x1=x + len(text), top=row * 10.0,
                                  bottom=row * 10.0 + 8.0, page=1, size=8.0))
                x += len(text) + 1
            made.append(Cell(words=tuple(spans)))
            x += 20.0
        built.append(Line(cells=tuple(made), page=1))
    return source_document.assemble(tuple(built))


# --------------------------------------------------------------------------- the control


def test_gold_grounds_completely_against_its_own_page(rendered):
    """The control. A value the renderer drew must be found where it was drawn."""
    suspicious = [
        (case.doc_id, g.field, g.value, g.coverage)
        for case in rendered.cases
        for g in resolve(case.source(), case.gold())
        if g.measured and g.suspicious
    ]
    assert suspicious == []


def test_the_control_is_not_vacuous(rendered):
    """A layer that declined to ask about everything would pass the control and mean nothing.

    The claim is a ratio, not a count: of the field instances that carry a value at all, the ones
    grounding refuses to ask about have to stay a small minority. Asserting a raw number instead
    would only be asserting the size of this fixture.
    """
    answered = [
        g for case in rendered.cases for g in resolve(case.source(), case.gold())
        if g.support is not Support.ABSENT
    ]
    measured = [g for g in answered if g.measured]

    assert len(measured) / len(answered) > 0.85, "NOT_PRINTED has swallowed the corpus"
    assert len({g.field for g in measured}) >= 15, "the control has to span the field set"
    assert all(g.support is Support.GROUNDED for g in measured)


# --------------------------------------------------------------------------- what it refuses to ask


def test_the_invoice_kind_is_not_a_question_the_page_can_answer(rendered):
    """`KOR` is an FA(3) code; the page says *Faktura korygująca*. A match would prove nothing."""
    assert "kind" in NOT_PRINTED
    kinds = [g for case in rendered.cases for g in resolve(case.source(), case.gold())
             if g.field == "kind"]
    assert kinds and all(g.support is Support.NOT_PRINTED for g in kinds)
    assert not any(g.measured for g in kinds)


def test_a_non_numeric_rate_is_not_asked_about_but_a_numeric_one_is(rendered):
    """The `oo` code's usual abbreviation is a substring of `sp. z o.o.` — see `resolve`."""
    rates = [g for case in rendered.cases for g in resolve(case.source(), case.gold())
             if g.field == "lines[].vat_rate"]
    printed = {g.value for g in rates if g.measured}
    withheld = {g.value for g in rates if g.support is Support.NOT_PRINTED}

    assert printed, "a numeric rate is on the page and must be grounded like anything else"
    assert all(value and value.isdigit() for value in printed)
    assert all(value and not value.isdigit() for value in withheld)


def test_a_field_the_invoice_does_not_carry_is_absent_not_ungrounded(rendered):
    absent = [g for case in rendered.cases for g in resolve(case.source(), case.gold())
              if g.support is Support.ABSENT]
    assert absent, "the corpus carries rows without a discount"
    assert all(g.coverage is None and not g.measured and not g.suspicious for g in absent)


def test_a_page_with_no_text_is_answered_no_text_and_never_ungrounded(rendered):
    """M7c's 3989 false alarms, at the unit that produced them.

    A rasterised scan carries no text layer, so there is nothing to search — and the first version
    answered `UNGROUNDED` for every value anyway, which claims the value is *missing from the page*
    when the page is missing. On a correct reading that is a false alarm per asserted value, and
    `oracle` drew 3989 of them. Not one may survive.
    """
    #: What `degrade/page.py` actually produces on a rung with no text layer: no words, so no
    #: lines, so nothing to assemble. Built through `assemble` rather than stubbed, so the test
    #: fails if that ever stops being the shape a scan comes back as.
    blank = source_document.assemble(())
    assert not blank.text.strip(), "the fixture has to be the page this test is about"

    case = rendered.cases[0]
    grounded = resolve(blank, case.gold())
    asked = [g for g in grounded if g.support is not Support.ABSENT]

    assert asked, "a real invoice asserts values, blank page or not"
    assert not any(g.support is Support.UNGROUNDED for g in asked), "no page, so no accusation"
    assert not any(g.measured or g.suspicious for g in asked)
    assert {g.support for g in asked} == {Support.NO_TEXT, Support.NOT_PRINTED}


def test_a_document_of_nothing_but_separators_is_still_a_document_with_no_text(rendered):
    """`readable` tests `strip()` rather than emptiness, and this is the branch that needs it.

    `source/document.py` joins cells with a tab and lines with a newline, so a document reduced to
    whitespace is the shape the separators leave behind. An emptiness test would call it searchable
    and hand every value on it an `UNGROUNDED` it had not earned — the same defect in a rarer form,
    which is exactly the kind that survives a fix aimed at the common one.
    """
    whitespace = source_document.SourceDocument(text="\t\n\n", words=(), cells=(), pages=1)
    assert whitespace.text and not whitespace.text.strip()

    supports = {g.support for g in resolve(whitespace, rendered.cases[0].gold())}
    assert Support.UNGROUNDED not in supports
    assert Support.NO_TEXT in supports


def test_a_code_the_page_never_prints_stays_not_printed_even_when_there_is_no_page(rendered):
    """The two exclusions are orthogonal, and the order in `_ground` is what keeps them so.

    `NOT_PRINTED` is a property of the field: `kind` is unanswerable on any page at all. Letting
    `NO_TEXT` swallow it would make a scanned run's two exclusion counts incomparable with a clean
    run's, and subtracting one from the other is exactly what a reader of the two reports does.
    """
    case = rendered.cases[0]
    on_a_real_page = {(g.field, g.key) for g in resolve(case.source(), case.gold())
                      if g.support is Support.NOT_PRINTED}
    on_no_page = {(g.field, g.key) for g in resolve(source_document.assemble(()), case.gold())
                  if g.support is Support.NOT_PRINTED}

    assert on_a_real_page and on_no_page == on_a_real_page


# --------------------------------------------------------------------------- the search itself


def test_a_value_inside_a_longer_cell_is_found(invoice):
    """One layout prints a whole row as prose, so the figure is never a cell of its own."""
    page = _page([["2", "usl.", "x", "706,26", "=", "netto", "1", "412,52,", "VAT", "23%"]])
    grounded = {
        (g.field, g.key): g
        for g in resolve(page, invoice.model_copy(update={"total_gross": Decimal("1412.52")}))
    }
    assert grounded[("total_gross", "")].support is Support.GROUNDED


def test_a_figure_does_not_ground_against_part_of_a_longer_one(invoice):
    """`52` is not on a page that prints `1 412,52`, and neither is `1412`."""
    page = _page([["netto", "1", "412,52"]])
    for amount in ("52", "1412", "412"):
        one = invoice.model_copy(update={"total_gross": Decimal(amount)})
        grounded = {g.field: g for g in resolve(page, one)}
        assert grounded["total_gross"].support is Support.UNGROUNDED, amount


def test_a_trailing_comma_does_not_look_like_a_decimal_point(invoice):
    """`netto 1 412,52, VAT` — the second comma ends a clause, and cost a real hit to get wrong."""
    page = _page([["netto", "1", "412,52,", "VAT"]])
    one = invoice.model_copy(update={"total_gross": Decimal("1412.52")})
    assert {g.field: g for g in resolve(page, one)}["total_gross"].support is Support.GROUNDED


def test_an_account_number_grounds_through_its_grouping_and_its_label(invoice):
    page = _page([["Rachunek:", "PL", "61", "1090", "1014", "0000", "0712", "1981", "2874",
                   "(Bank", "Spółdzielczy)"]])
    grounded = {g.field: g for g in resolve(page, invoice)}
    assert grounded["payment_account"].support is Support.GROUNDED
    assert grounded["payment_account"].spans


def test_an_identifier_does_not_ground_inside_a_longer_run_of_digits(invoice):
    """A NIP that happens to be a slice of an account number was not read off the page."""
    page = _page([["Konto", "99911302201899123456"]])
    grounded = {g.field: g for g in resolve(page, invoice)}
    assert grounded["seller.nip"].support is Support.UNGROUNDED


# --------------------------------------------------------------------------- text and coverage


def test_a_description_wrapped_around_its_own_row_still_grounds(invoice):
    """The renderer puts a long description above and below the numbers. It is one description."""
    page = _page(
        [["Wynajem", "powierzchni"]],
        [["1", "m2", "31", "43,12"]],
        [["magazynowej"]],
    )
    one = invoice.model_copy(update={
        "lines": (invoice.lines[0].model_copy(
            update={"description": "Wynajem powierzchni magazynowej"}),),
    })
    grounded = {(g.field, g.key): g for g in resolve(page, one)}
    assert grounded[("lines[].description", "1")].support is Support.GROUNDED


def test_a_description_the_model_invented_does_not_ground(invoice):
    page = _page([["Wynajem", "powierzchni", "magazynowej"]])
    one = invoice.model_copy(update={
        "lines": (invoice.lines[0].model_copy(update={"description": "Konsultacje prawnicze"}),),
    })
    grounded = {(g.field, g.key): g for g in resolve(page, one)}
    assert grounded[("lines[].description", "1")].support is Support.UNGROUNDED


def test_half_a_description_found_is_partial_and_suspicious(invoice):
    """The shape a fabricated continuation takes, and the reason there are three levels."""
    page = _page([["Wynajem", "powierzchni"]])
    one = invoice.model_copy(update={
        "lines": (invoice.lines[0].model_copy(
            update={"description": "Wynajem powierzchni biurowej natychmiast"}),),
    })
    grounded = {(g.field, g.key): g for g in resolve(page, one)}[("lines[].description", "1")]

    assert grounded.support is Support.PARTIAL
    assert 0.0 < (grounded.coverage or 0) < 1.0
    assert grounded.suspicious


def test_a_word_claimed_twice_needs_the_page_to_print_it_twice(invoice):
    page = _page([["Usługa", "transportowa"]])
    one = invoice.model_copy(update={
        "lines": (invoice.lines[0].model_copy(update={"description": "Usługa Usługa"}),),
    })
    grounded = {(g.field, g.key): g for g in resolve(page, one)}[("lines[].description", "1")]
    assert grounded.support is Support.PARTIAL
    assert grounded.coverage == 0.5


def test_punctuation_a_join_introduced_is_not_looked_for(invoice):
    """The gold joins an address's lines with a comma the page never drew."""
    page = _page([["Rynek", "4"]], [["50-106", "Wrocław"]])
    one = invoice.model_copy(update={
        "buyer": invoice.buyer.model_copy(update={"address": "Rynek 4, 50-106 Wrocław"}),
    })
    assert {g.field: g for g in resolve(page, one)}["buyer.address"].support is Support.GROUNDED


# --------------------------------------------------------------------------- surface forms


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("137.3"), "137,30"),     # gold holds three digits, the page printed four
        (Decimal("137.30"), "137,3"),     # and the other direction
        (Decimal("1336.72"), "1 336,72"),
        (Decimal("1336.72"), "1336.72"),
    ],
)
def test_an_amount_offers_the_forms_a_polish_invoice_prints(value, expected):
    assert expected in surface.candidates("lines[].net", value)


def test_a_date_offers_iso_and_the_dotted_form():
    forms = surface.candidates("issue_date", dt.date(2026, 6, 8))
    assert "2026-06-08" in forms
    assert "08.06.2026" in forms


def test_a_numeric_rate_offers_itself_with_and_without_a_percent_sign():
    assert set(surface.candidates("lines[].vat_rate", "23")) >= {"23", "23%"}


def test_the_page_and_the_candidate_go_through_one_function():
    """The bug this replaced: normalising the two sides differently, so neither ever matched."""
    nbsp = chr(0x00A0)
    assert surface.amount_form(f"1{nbsp}336,72") == surface.amount_form("1 336,72") == "1 336.72"


# --------------------------------------------------------------------------- the boundary


def test_grounding_knows_nothing_about_the_renderer():
    """It matches values, never labels. `eval/pattern.py` is allowed to; this package is not."""
    from pathlib import Path

    package = Path(resolve.__module__.replace(".", "/")).parent
    sources = [
        (Path("src") / package / name).read_text(encoding="utf-8")
        for name in ("resolve.py", "surface.py", "__init__.py")
    ]
    for text in sources:
        assert "doc_extract.synth" not in text
        for label in ("Numer faktury", "Do zapłaty", "Sprzedawca", "Rachunek:"):
            assert f'"{label}' not in text, f"a printed label leaked into grounding: {label}"
