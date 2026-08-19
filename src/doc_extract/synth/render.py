"""Three ways to print the same invoice, so a result never confounds difficulty with layout.

An extractor evaluated on one template can only be said to read *that* template. The three here
differ in the way that matters for a text layer: the order values come out in. `classic` puts the
totals in a right-aligned block after the rows; `ledger` folds a per-rate summary into the item
table itself, so rate figures arrive interleaved with rows; `compact` abandons the table entirely
and prints each position as running text, which puts the description immediately before its own
amounts instead of columns away.

**Every value in the gold is printed.** A page from which a gold field could not be read would make
the extraction task unsolvable and the metric meaningless; `tests/test_synth_render.py` asserts the
recovery of every one of them through `pdfplumber`. That is also why an eight-decimal unit price is
printed to eight decimals — showing a tidier two would put a number on the page that is not the
number in the gold.

The discount is the case that proves why the claim needs a test rather than a docstring. `P_10` was
in the gold and in the XML but on no layout, and because it is folded into `net`, its absence did
not merely make one field unrecoverable — it made the page's own arithmetic contradict itself, so a
reader who read the page perfectly still tripped `lines.net_matches_quantity_times_price` on every
document carrying one. A generator defect was therefore being charged to the extractor, in the one
metric the project exists to report.

Rendering is deterministic: `rl_config.invariant` strips the creation timestamp and the document id
that would otherwise make two renders of one invoice differ byte for byte.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from importlib import resources
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from doc_extract.schema.ksef import Invoice, LineItem
from doc_extract.synth import overlay as overlay_module
from doc_extract.synth import pools
from doc_extract.synth.build import Document

#: Fixed so two renders of one document are byte-identical; a corpus that changed on every run
#: could not be checksummed, and a manifest of unstable hashes would be worse than none.
rl_config.invariant = 1

#: Resolved through the package rather than by walking up from `__file__`. The fonts used to live
#: outside `src/`, found by counting three parents — which is the repository layout, not the
#: package's, so anything but an editable install put them somewhere the count did not reach.
#: Shipping them as package data makes the location a property of the package instead.
FONT_DIR = Path(str(resources.files("doc_extract").joinpath("assets", "fonts")))
REGULAR = "DejaVuSans"
BOLD = "DejaVuSans-Bold"

TEMPLATES: tuple[str, ...] = ("classic", "ledger", "compact")

#: Page margins per layout, in millimetres. `compact` is the wide-margin one; the two that carry an
#: item table are held to what the table needs, because a Polish invoice contains words like
#: `wewnątrzwspólnotowa` (34.3 mm at the cell's own size) and reportlab breaks a word too long for
#: its column mid-syllable rather than letting it overrun. The layouts differ in the order values
#: come out in, which is what a text layer sees; the margin was never doing that work.
MARGINS: dict[str, float] = {"classic": 15, "ledger": 14, "compact": 22}

#: Printable width of an A4 page inside each layout's margins.
PRINTABLE: dict[str, float] = {name: 210 - 2 * margin for name, margin in MARGINS.items()}

#: Item-table columns, in millimetres and in print order.
#:
#: A table wider than its page does not wrap. reportlab draws it past the edge and the rightmost
#: column simply falls off, and a column narrower than its widest value spills into its neighbour —
#: where `0% WDT` ends up fused to the net beside it into a single word with a single bounding box,
#: which is worse than a flat-text ambiguity because word geometry cannot separate it either. Both
#: are silent, so `tests/test_synth_render.py` measures every fixed-content cell against its column.
#:
#: Only the discount column is new against a conventional invoice layout, and it displaced the line
#: gross that `classic` used to carry. The rule that settled it: a column earns its width by holding
#: something the page would otherwise lose. `P_10` is a gold field and folded into `net`, so a page
#: without it states `quantity x price != net` and no reader can explain the gap; a line's gross is
#: the sum of the two cells beside it and costs nothing to omit.
#: Widths are set against the widest value a column can ever hold, not the widest one this seed
#: happens to draw — a correction prints every amount and quantity with a leading minus, which is
#: about a millimetre nobody budgets for until a re-seed silently overruns.
ITEM_COLUMNS: dict[str, tuple[float, ...]] = {
    "classic": (9, 35, 13, 16, 28, 18, 20, 21, 19),   # 179 of 180 mm
    "ledger": (10, 37, 13, 16, 28, 18, 20, 21, 19),   # 182 of 182 mm
}

#: The column holding the description. It is the one column whose content wraps, which is exactly
#: why it needs its own floor: a `Paragraph` splits a word that cannot fit, so a column too narrow
#: does not overrun visibly — it silently prints `wewnątrzwspól` and `notowa` on separate lines and
#: the word is no longer on the page at all.
DESCRIPTION_COLUMN = 1

ITEM_HEADERS: tuple[str, ...] = (
    "Lp.", "Nazwa towaru lub usługi", "J.m.", "Ilość", "Cena netto", "Rabat",
    "Wartość netto", "VAT", "Kwota VAT",
)

#: The column each layout prints the unit price in — the widest value any cell has to hold, since
#: `TKwotowy2` allows eight fractional digits.
PRICE_COLUMN = 4

#: Headers are laid out as `Paragraph`s so a long one wraps inside its column instead of spilling.
#: `Wartość netto` and `Kwota VAT` are both wider than the columns their values need, and a header
#: that overruns fuses with its neighbour in the text layer exactly as an oversized value does.
HEADER_SIZE = 7.5

#: Rate code -> what the page prints for it. The mapping is injective on purpose: `fa3_xml` refuses
#: to write a rate the document could not state unambiguously (`rate_slots.AMBIGUOUS`), and a
#: renderer that collapsed `np I` and `np II` to one label would be quietly reintroducing on the
#: page the ambiguity the XML side rejects — printing a value the gold distinguishes and no reader
#: could. `tests/test_synth_render.py` asserts the injectivity, so a new code cannot re-collapse it.
_RATE_LABELS = {
    "23": "23%", "8": "8%", "5": "5%", "0 KR": "0%", "0 WDT": "0% WDT", "0 EX": "0% eksport",
    "zw": "zw.", "oo": "o.o.", "np I": "np (I)", "np II": "np (II)",
}


def _register_fonts() -> None:
    """DejaVu carries the Polish diacritics; the fonts reportlab ships with do not.

    Twelve of the eighteen accented Polish letters are missing from the bundled Vera family, so an
    invoice set in it would silently drop them — a corpus with no `ą` or `ł` would be easier to
    read than a real page in exactly the respect that matters.
    """
    if REGULAR in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(TTFont(REGULAR, str(FONT_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(BOLD, str(FONT_DIR / "DejaVuSans-Bold.ttf")))


@dataclass(frozen=True, slots=True)
class Rendered:
    """The PDF and the one fact about it the manifest needs but the bytes do not readily give."""

    data: bytes
    pages: int


def render(document: Document) -> Rendered:
    """The document as a PDF, in whichever of the three layouts it was assigned."""
    _register_fonts()
    builder = {"classic": _classic, "ledger": _ledger, "compact": _compact}[document.template]
    margin = MARGINS[document.template] * mm

    buffer = _BytesTarget()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, title=document.invoice.number, author=document.invoice.seller.name,
        leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=18 * mm,
    )
    made: list[_PagedCanvas] = []

    def canvasmaker(*args, **kwargs) -> _PagedCanvas:
        canvas = _PagedCanvas(*args, **kwargs)
        made.append(canvas)
        return canvas

    doc.build(builder(document), canvasmaker=canvasmaker)
    return Rendered(data=buffer.value, pages=made[-1].page_count)


# --------------------------------------------------------------------------- layouts


def _classic(document: Document) -> list[Flowable]:
    invoice, context = document.invoice, document.context
    story: list[Flowable] = [
        Paragraph(_title(invoice), _style("title", size=15, font=BOLD)),
        Paragraph(f"{context.place}, {invoice.issue_date:%d.%m.%Y}",
                  _style("right", align=TA_RIGHT)),
        Spacer(1, 6 * mm),
        _meta_table(document),
        Spacer(1, 5 * mm),
        _party_columns(document),
        Spacer(1, 6 * mm),
        _items_table(document, layout="classic"),
        Spacer(1, 4 * mm),
        _totals_block(document, align="right"),
        Spacer(1, 6 * mm),
    ]
    story += _payment_block(document)
    story += _notes(document)
    story += _overlay_tail(document)
    return story


def _ledger(document: Document) -> list[Flowable]:
    """The per-rate summary lives inside the item table, so rate figures interleave with rows."""
    invoice, context = document.invoice, document.context
    story: list[Flowable] = [
        Paragraph(invoice.seller.name, _style("vendor", size=12, font=BOLD)),
        Paragraph(context.seller.address_line, _style("vendor_addr", size=8)),
        Paragraph(f"NIP {pools.format_nip(invoice.seller.nip)}", _style("vendor_nip", size=8)),
        Spacer(1, 4 * mm),
        Paragraph(_title(invoice), _style("title_l", size=14, font=BOLD)),
        _meta_table(document),
        Spacer(1, 4 * mm),
        _buyer_box(document),
        Spacer(1, 4 * mm),
        _items_table(document, layout="ledger", summary_rows=True),
        Spacer(1, 4 * mm),
        _totals_block(document, align="left"),
        Spacer(1, 5 * mm),
    ]
    story += _payment_block(document)
    story += _notes(document)
    story += _overlay_tail(document)
    return story


def _compact(document: Document) -> list[Flowable]:
    """No table at all: each position is a paragraph, so its amounts sit next to its description."""
    invoice, context = document.invoice, document.context
    story: list[Flowable] = [
        Paragraph(_title(invoice), _style("title_c", size=13, font=BOLD)),
        Paragraph(
            f"Wystawiono: {context.place}, {invoice.issue_date:%Y-%m-%d}"
            + (f" &nbsp;·&nbsp; Data sprzedaży: {invoice.sale_date:%Y-%m-%d}"
               if invoice.sale_date is not None else ""),
            _style("meta_c", size=8),
        ),
        Spacer(1, 4 * mm),
        Paragraph("<b>Sprzedawca</b>", _style("h_s", size=9)),
        Paragraph(_party_text(invoice.seller.name, invoice.seller.nip, context.seller),
                  _style("p_s", size=9)),
        Spacer(1, 2 * mm),
        Paragraph("<b>Nabywca</b>", _style("h_b", size=9)),
        Paragraph(_party_text(invoice.buyer.name, invoice.buyer.nip, context.buyer),
                  _style("p_b", size=9)),
        Spacer(1, 5 * mm),
        Paragraph("<b>Pozycje</b>", _style("h_i", size=9)),
    ]
    for index, (line, unit) in enumerate(zip(invoice.lines, context.line_units, strict=True)):
        story.append(KeepTogether([
            Paragraph(f"{line.line_no}. {_described(document, line, index)}",
                      _style("i_d", size=9)),
            Paragraph(_position_text(line, unit), _style("i_a", size=8)),
            Spacer(1, 1.5 * mm),
        ]))
    story += [Spacer(1, 3 * mm), _totals_block(document, align="left"), Spacer(1, 4 * mm)]
    story += _payment_block(document)
    story += _notes(document)
    story += _overlay_tail(document)
    return story


# --------------------------------------------------------------------------- shared blocks


def _meta_table(document: Document) -> Table:
    invoice = document.invoice
    rows = [
        ["Numer faktury:", invoice.number],
        ["Data wystawienia:", f"{invoice.issue_date:%Y-%m-%d}"],
    ]
    #: `sale_date` is optional in the schema, and formatting `None` raises rather than printing
    #: something odd. `build` always sets it, so this is unreachable from the corpus — but the row
    #: belongs to a document that may not have one, and a renderer that crashed on a lawful invoice
    #: would be a poor thing to discover from a real held-out set in M7.
    if invoice.sale_date is not None:
        rows.append(["Data sprzedaży:", f"{invoice.sale_date:%Y-%m-%d}"])
    rows.append(["Waluta:", invoice.currency])
    if document.context.corrected_number is not None:
        rows.append(["Faktura korygowana:", document.context.corrected_number])
        rows.append(["z dnia:", f"{document.context.corrected_date:%Y-%m-%d}"])
    return _plain_table(rows, widths=(42 * mm, 78 * mm), size=9)


def _party_columns(document: Document) -> Table:
    invoice, context = document.invoice, document.context
    table = Table(
        [[
            Paragraph("<b>Sprzedawca</b><br/>"
                      + _party_text(invoice.seller.name, invoice.seller.nip, context.seller),
                      _style("col_s", size=9)),
            Paragraph("<b>Nabywca</b><br/>"
                      + _party_text(invoice.buyer.name, invoice.buyer.nip, context.buyer),
                      _style("col_b", size=9)),
        ]],
        colWidths=(87 * mm, 87 * mm),
    )
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _buyer_box(document: Document) -> Table:
    invoice, context = document.invoice, document.context
    table = Table(
        [[Paragraph("<b>Nabywca</b><br/>"
                    + _party_text(invoice.buyer.name, invoice.buyer.nip, context.buyer),
                    _style("box_b", size=9))]],
        colWidths=(95 * mm,),
    )
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _items_table(document: Document, *, layout: str, summary_rows: bool = False) -> Table:
    invoice, context = document.invoice, document.context
    rows: list[list] = [
        [Paragraph(text, _style("th", size=HEADER_SIZE, font=BOLD)) for text in ITEM_HEADERS]
    ]
    for index, (line, unit) in enumerate(zip(invoice.lines, context.line_units, strict=True)):
        rows.append([
            str(line.line_no),
            Paragraph(_described(document, line, index), _style("cell", size=7.5)),
            unit,
            _quantity(line.quantity),
            _price(line.unit_price_net),
            _discount(line.discount),
            _amount(line.net),
            _RATE_LABELS[line.vat_rate],
            _amount(line.vat),
        ])

    if summary_rows:
        for total in invoice.rate_totals:
            rows.append(["", f"Razem {_RATE_LABELS[total.rate]}", "", "", "", "",
                         _amount(total.net), _RATE_LABELS[total.rate], _amount(total.vat)])

    widths = [width * mm for width in ITEM_COLUMNS[layout]]
    table = Table(rows, colWidths=widths, repeatRows=1)
    style = [
        ("FONT", (0, 1), (-1, -1), REGULAR, 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#666666")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    if summary_rows:
        first = len(invoice.lines) + 1
        style.append(("FONT", (0, first), (-1, -1), BOLD, 8))
    table.setStyle(TableStyle(style))
    return table


def _totals_block(document: Document, *, align: str) -> Table:
    invoice = document.invoice
    rows = [["Stawka", "Netto", "VAT", "Brutto"]]
    for total in invoice.rate_totals:
        rows.append([
            _RATE_LABELS[total.rate], _amount(total.net), _amount(total.vat),
            _amount(total.net + total.vat),
        ])
    rows.append(["Razem", "", "", _amount(invoice.total_gross)])

    table = Table(rows, colWidths=(24 * mm, 30 * mm, 28 * mm, 30 * mm),
                  hAlign="RIGHT" if align == "right" else "LEFT")
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), BOLD, 8),
        ("FONT", (0, 1), (-1, -2), REGULAR, 9),
        ("FONT", (0, -1), (-1, -1), BOLD, 10),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#666666")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    return table


def _payment_block(document: Document) -> list[Flowable]:
    invoice, context = document.invoice, document.context
    lines = [
        f"Do zapłaty: <b>{_amount(invoice.total_gross)} {invoice.currency}</b>",
        f"Termin płatności: {context.payment_due:%Y-%m-%d}",
        f"Forma płatności: {context.payment_form[1]}",
    ]
    if invoice.payment_account is not None:
        lines.append(f"Rachunek: {pools.format_iban(invoice.payment_account)} "
                     f"({context.bank_name})")
    return [Paragraph("<br/>".join(lines), _style("pay", size=9)), Spacer(1, 4 * mm)]


def _notes(document: Document) -> list[Flowable]:
    """The annotations and the trimmings that are on the page but not in the extraction schema."""
    context = document.context
    notes: list[str] = []
    if context.annotations.split_payment:
        notes.append("mechanizm podzielonej płatności")
    if context.annotations.reverse_charge:
        notes.append("odwrotne obciążenie")
    if context.annotations.exempt:
        notes.append("zwolnione z VAT — art. 43 ust. 1 ustawy o podatku od towarów i usług")
    if context.fx_rate is not None:
        notes.append(
            f"kurs NBP z dnia {context.fx_date:%Y-%m-%d}: 1 {document.invoice.currency} = "
            f"{_amount(context.fx_rate, places=4)} PLN; podatek w PLN: "
            + ", ".join(_amount(value) for value in context.vat_in_pln)
        )
    if context.correction_reason is not None:
        notes.append(f"przyczyna korekty: {context.correction_reason}")
    if context.gross_before_correction is not None:
        notes.append(f"kwota przed korektą: {_amount(context.gross_before_correction)}")
    if context.order_value is not None:
        notes.append(f"wartość zamówienia: {_amount(context.order_value)} "
                     f"{document.invoice.currency}")
    injected = _overlay_at(document, overlay_module.ANNOTATIONS)
    if injected is not None:
        notes.append(escape(injected))
    if not notes:
        return []
    return [Paragraph("Adnotacje: " + "; ".join(notes), _style("notes", size=8))]


# --------------------------------------------------------------------------- overlay


def _overlay_at(document: Document, placement: str) -> str | None:
    """The overlay's text if it belongs at this placement, and `None` otherwise.

    Whitespace is collapsed on the way out. A payload is written as a paragraph with newlines in the
    source that defines it, and reportlab treats a newline as a space anyway — collapsing here means
    the text on the page is a function of the payload's words rather than of how they were wrapped
    in a Python string, which is what keeps the rendered bytes stable when a payload is reformatted.
    """
    overlay = document.overlay
    if overlay is None or not overlay.at(placement):
        return None
    return " ".join(overlay.text.split())


def _described(document: Document, line: LineItem, index: int) -> str:
    """A row's description, with the overlay appended when it is placed inside the item table.

    The **first** row, always. Not a random one and not the last: an attack whose position varied
    with the document would make a per-placement success rate a mixture of two things, and the row
    that is certain to exist is the first one.
    """
    description = escape(line.description or "")
    injected = _overlay_at(document, overlay_module.DESCRIPTION) if index == 0 else None
    return description if injected is None else f"{description} {escape(injected)}"


def _overlay_tail(document: Document) -> list[Flowable]:
    """The two placements that print as a paragraph of their own, after everything else.

    `invisible` differs from `footer` in one attribute — the ink is white — and that single
    attribute is the realistic version of this attack: a human approving the invoice sees nothing,
    while the text layer `source/` reads carries every word. Whether that is true of *this*
    renderer is asserted rather than asserted-in-prose; `tests/test_synth_overlay.py` reads the
    payload back out of the PDF.
    """
    footer = _overlay_at(document, overlay_module.FOOTER)
    if footer is not None:
        return [Spacer(1, 3 * mm), Paragraph(escape(footer), _style("overlay", size=8))]

    hidden = _overlay_at(document, overlay_module.INVISIBLE)
    if hidden is not None:
        return [
            Spacer(1, 3 * mm),
            Paragraph(escape(hidden), _style("overlay_h", size=7, color=colors.white)),
        ]
    return []


# --------------------------------------------------------------------------- formatting


def _title(invoice: Invoice) -> str:
    label = {"KOR": "Faktura korygująca", "ZAL": "Faktura zaliczkowa"}.get(invoice.kind, "Faktura")
    return f"{label} nr {invoice.number}"


def _party_text(name: str, nip: str | None, company: pools.Company) -> str:
    parts = [name, company.street, f"{company.postcode} {company.city}"]
    if nip is not None:
        parts.append(f"NIP: {pools.format_nip(nip)}")
    return "<br/>".join(parts)


def _position_text(line: LineItem, unit: str) -> str:
    rebate = f" (rabat {_amount(line.discount)})" if line.discount is not None else ""
    return (
        f"{_quantity(line.quantity)} {unit} × {_price(line.unit_price_net)}{rebate} = "
        f"netto {_amount(line.net)}, VAT {_RATE_LABELS[line.vat_rate]} {_amount(line.vat)}, "
        f"brutto {_amount(line.net + line.vat)}"
    )


def _discount(value: Decimal | None) -> str:
    """An empty cell when there is no discount, because `P_10` is absent rather than zero.

    Printing `0,00` would put a number in the gold's place that the gold does not carry, and an
    extractor reading it back would be right to return zero where the document says nothing.
    """
    return "" if value is None else _amount(value)


def _price(value: Decimal) -> str:
    """A unit price at its own precision, however many places that is.

    `TKwotowy2` allows eight fractional digits and the rounding tier uses all of them. Printing a
    tidier two would put a number on the page that is not the number in the gold, which would make
    the field unrecoverable and the metric a measure of the generator's formatting.
    """
    return _amount(value, places=max(2, -value.as_tuple().exponent))


def _amount(value: Decimal, *, places: int = 2) -> str:
    """`1 234,56` — a space between thousands and a comma before the grosze, as Poland prints it.

    The extractor has to undo this, which is part of the task rather than an obstacle to it.
    """
    return f"{value:,.{places}f}".replace(",", "\x00").replace(".", ",").replace("\x00", " ")


def _quantity(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _plain_table(rows: list[list[str]], *, widths: tuple[float, ...], size: float) -> Table:
    table = Table(rows, colWidths=widths, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (0, -1), REGULAR, size),
        ("FONT", (1, 0), (1, -1), BOLD, size),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return table


def _style(name: str, *, size: float = 10, font: str = REGULAR,
           align: int | None = None, color: colors.Color | None = None) -> ParagraphStyle:
    style = ParagraphStyle(name, fontName=font, fontSize=size, leading=size * 1.3)
    if align is not None:
        style.alignment = align
    if color is not None:
        style.textColor = color
    return style


class _BytesTarget:
    """A minimal file-like sink; `SimpleDocTemplate` only ever writes and closes."""

    def __init__(self) -> None:
        self._chunks: list[bytes] = []

    def write(self, data: bytes) -> int:
        self._chunks.append(data)
        return len(data)

    def close(self) -> None:
        return None

    @property
    def value(self) -> bytes:
        return b"".join(self._chunks)


class _PagedCanvas(Canvas):
    """Prints `Strona 1 z 2`, which needs the page count and therefore a second pass."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._pages: list[dict] = []
        self.page_count = 0

    def showPage(self) -> None:
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._pages)
        for state in self._pages:
            #: Restoring a page's state overwrites every attribute, so anything recorded before
            #: this loop is lost — `page_count` has to be set after it, not before.
            self.__dict__.update(state)
            self.setFont(REGULAR, 7.5)
            self.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Strona {self._pageNumber} z {total}")
            super().showPage()
        super().save()
        self.page_count = total
