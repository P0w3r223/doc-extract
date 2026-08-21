"""How each foreign layout says it: the words, the separators, the order of the blocks.

A dialect is the whole of what a text layer sees, held as data so that the claim "this page does not
speak the corpus's language" is inspectable rather than buried in a renderer. Three of them, one per
layout, paired one-to-one on purpose: a per-template result is then interpretable, because template
and vocabulary are the same variable rather than two that vary independently.

**Every label here is a form a Polish invoice actually uses.** `Wystawca`, `Odbiorca`,
`Sprzedający`, `Płatnik`, `Kwota do zapłaty`, `Należność ogółem` are not invented alternatives —
they are what different vendors' accounting software prints. Inventing labels would make the corpus
harder in a way no real document is, and the result would measure robustness to nonsense instead of
robustness to the field.

**Nothing here may repeat what `synth/render.py` prints.** That is the entire point of the package,
so `tests/test_foreign_dialect.py` renders one document both ways and asserts that no label of a
dialect appears on the synthetic page. A single shared `Do zapłaty:` would let the pattern baseline
keep the one field that matters most, and the comparison would quietly stop being held-out.

**The number formats are constrained by more than taste**: `ground/surface.py` has to be able to
recognise a value it never saw rendered, and a format it cannot resolve would report a correctly
read figure as ungrounded — turning a property of this module into a finding about the detector. A
dot *between the thousands* — `1.234,56` — is a German convention rather than a Polish one and is
also the one form that normalisation could not undo, so its absence is a fact about Polish
typography that happens to be convenient. A dot before the *grosze* is neither: `surface` produces
both bodies, and `slip` prints it.

The rate labels are checked for injectivity the same way the synthetic renderer's are: a page that
wrote `np I` and `np II` the same way would state a value no reader could recover, and the gold
distinguishes them.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

#: The thousands separators the dialects use: a plain space, or nothing at all.
#:
#: A **non-breaking space** was the obvious third and is deliberately not here. It is a real Polish
#: convention, but `pdfplumber` returns it as a plain space and `source/document.py` reads the page
#: from word geometry, where a U+00A0 is a word boundary exactly as U+0020 is — so a dialect that
#: printed it would be identical to `letterhead` in the only place this corpus is measured, and the
#: page would carry a difference no reader could ever see. `ground/surface.GROUPING` normalises it
#: for the same reason, against pages this project does not render.
SPACE = " "
NONE = ""


@dataclass(frozen=True, slots=True)
class Numbers:
    """One dialect's way of writing a figure: what breaks the thousands, what marks the grosze."""

    grouping: str
    decimal: str

    def amount(self, value: Decimal, *, places: int = 2) -> str:
        return self.figure(f"{value:.{places}f}")

    def price(self, value: Decimal) -> str:
        """A unit price at its own precision, however many places the gold carries.

        `TKwotowy2` admits eight fractional digits and one tier uses all of them. Printing a tidier
        two would put a figure on the page that is not the figure in the gold, which makes the field
        unrecoverable and turns the metric into a measure of this module's formatting.
        """
        return self.amount(value, places=max(2, -value.as_tuple().exponent))

    def quantity(self, value: Decimal) -> str:
        text = format(value, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return self.figure(text)

    def figure(self, plain: str) -> str:
        """A plain `-1234.56` in this dialect's clothes — the one place a separator is applied."""
        sign, digits = ("-", plain[1:]) if plain.startswith("-") else ("", plain)
        whole, _, fraction = digits.partition(".")
        grouped = self._group(whole)
        return f"{sign}{grouped}{self.decimal}{fraction}" if fraction else f"{sign}{grouped}"

    def _group(self, whole: str) -> str:
        if not self.grouping or len(whole) <= 3:
            return whole
        return f"{self._group(whole[:-3])}{self.grouping}{whole[-3:]}"


@dataclass(frozen=True, slots=True)
class Dates:
    """One dialect's date format, named by the `strftime` pattern it prints."""

    pattern: str

    def format(self, value) -> str:
        return value.strftime(self.pattern)


@dataclass(frozen=True, slots=True)
class Dialect:
    """One foreign layout's whole vocabulary. Every string the page prints as a label is here."""

    name: str
    numbers: Numbers
    dates: Dates

    title_vat: str
    title_correction: str
    title_advance: str

    seller: str
    buyer: str
    number: str
    issued: str
    sold: str
    currency: str
    due: str
    payment_form: str
    account: str
    payable: str
    notes: str
    corrected: str
    corrected_on: str
    tax_id: str

    #: The item table's headers, in the order this layout prints its columns. The order is part of
    #: the dialect because it is the strongest thing a column-position reader depends on.
    columns: tuple[str, ...]
    #: The per-rate summary's headers.
    summary: tuple[str, ...]
    summary_total: str

    def labels(self) -> tuple[str, ...]:
        """Every label this dialect prints, for the disjointness check the package rests on."""
        return (
            self.title_vat, self.title_correction, self.title_advance,
            self.seller, self.buyer, self.number, self.issued, self.sold, self.currency,
            self.due, self.payment_form, self.account, self.payable, self.notes,
            self.corrected, self.corrected_on, self.tax_id,
            *self.columns, *self.summary, self.summary_total,
        )


#: How a rate code is printed. Injective, for the reason `synth/render.py` gives and the test
#: repeats: the gold distinguishes `np I` from `np II`, so a page that wrote them the same way would
#: state a value no reader could recover, and the field would be unscorable rather than hard.
#:
#: Written out rather than abbreviated to two letters: `oo` printed as `o.o.` is a substring of
#: `sp. z o.o.`, the legal form half the sellers in the pool carry, and a value that grounds against
#: its seller's suffix is worse than one that does not ground at all.
RATE_LABELS: dict[str, str] = {
    "23": "23 %",
    "8": "8 %",
    "5": "5 %",
    "0 KR": "0 % kraj",
    "0 WDT": "0 % WDT",
    "0 EX": "0 % eksport",
    "zw": "zwolniona",
    "oo": "odwr. obc.",
    "np I": "np. I",
    "np II": "np. II",
}


LETTERHEAD = Dialect(
    name="letterhead",
    numbers=Numbers(grouping=SPACE, decimal=","),
    dates=Dates(pattern="%d.%m.%Y"),
    title_vat="FAKTURA",
    title_correction="FAKTURA KORYGUJĄCA",
    title_advance="FAKTURA ZALICZKOWA",
    seller="Wystawca",
    buyer="Odbiorca",
    number="Nr dokumentu",
    issued="Wystawiono",
    sold="Data dostawy",
    currency="Waluta rozliczenia",
    due="Płatne do",
    payment_form="Sposób zapłaty",
    account="Nr rachunku",
    payable="Kwota do zapłaty",
    notes="Uwagi",
    corrected="Koryguje dokument",
    corrected_on="wystawiony",
    tax_id="NIP",
    columns=("Poz.", "Towar / usługa", "Stawka", "Ilość", "Cena jedn. netto", "Upust",
             "Wartość netto", "Podatek"),
    summary=("Wg stawki", "Podstawa", "Podatek", "Wartość"),
    summary_total="Ogółem",
)

STATEMENT = Dialect(
    name="statement",
    numbers=Numbers(grouping=NONE, decimal=","),
    dates=Dates(pattern="%Y-%m-%d"),
    title_vat="Faktura VAT",
    title_correction="Korekta faktury VAT",
    title_advance="Faktura zaliczkowa VAT",
    seller="Sprzedający",
    buyer="Kupujący",
    number="Faktura nr",
    issued="Sporządzono dnia",
    sold="Data wykonania",
    currency="Rozliczenie w",
    due="Zapłata do dnia",
    payment_form="Tryb zapłaty",
    account="Konto",
    payable="Należność ogółem",
    notes="Informacje dodatkowe",
    corrected="Dotyczy faktury",
    corrected_on="z dnia wystawienia",
    tax_id="NIP",
    #: The description **last**. A reader that found the name by looking at the second column of a
    #: row finds a quantity here, and that is the failure worth provoking.
    columns=("Poz.", "Ilość", "Cena jedn. netto", "Upust", "Wartość netto", "Stawka", "Podatek",
             "Towar / usługa"),
    summary=("Wg stawki", "Podstawa", "Podatek", "Wartość"),
    summary_total="Suma",
)

SLIP = Dialect(
    name="slip",
    #: A **dot** before the grosze, with a space still breaking the thousands. Not the Polish
    #: convention and not a mistake either: it is what accounting software that was never localised
    #: prints, and a Polish business receiving invoices from a foreign system meets it constantly.
    #: It is also the one variation `eval/pattern.py` cannot survive — its amount regex requires a
    #: decimal comma — which is the point of putting a held-out set in front of a fitted reader.
    numbers=Numbers(grouping=SPACE, decimal="."),
    dates=Dates(pattern="%d-%m-%Y"),
    title_vat="Dokument sprzedaży",
    title_correction="Dokument korygujący sprzedaż",
    title_advance="Dokument zaliczkowy",
    seller="Dostawca",
    buyer="Płatnik",
    number="Dokument nr",
    issued="Dnia",
    sold="Wydano dnia",
    currency="W walucie",
    due="Termin zapłaty",
    payment_form="Zapłata",
    account="Rachunek do wpłaty",
    payable="Razem do zapłaty",
    notes="Zastrzeżenia",
    corrected="Do dokumentu",
    corrected_on="z",
    tax_id="NIP",
    #: `slip` prints positions as running text and has no table, so its columns are the words that
    #: separate the figures in a position line. They are labels all the same, and the disjointness
    #: check has to see them.
    columns=("po", "upust", "netto", "podatek", "brutto"),
    summary=("Wg stawki", "Podstawa", "Podatek", "Wartość"),
    summary_total="Łącznie",
)

DIALECTS: tuple[Dialect, ...] = (LETTERHEAD, STATEMENT, SLIP)

BY_NAME: dict[str, Dialect] = {dialect.name: dialect for dialect in DIALECTS}

TEMPLATES: tuple[str, ...] = tuple(dialect.name for dialect in DIALECTS)
