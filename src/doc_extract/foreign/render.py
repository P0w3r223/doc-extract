"""Three unfamiliar pages for an invoice this project already knows.

What a text layer sees is the order values come out in and the words beside them, so that is what
these three vary — against `synth/render.py` and against each other:

* **`letterhead`** puts the two parties in side-by-side boxes and the per-rate summary *above* the
  payment block, and its item table opens with the rate rather than closing with it.
* **`statement`** prints the totals **before** the rows, so a reader meets the amount payable
  before it has met anything it summarises, and its item table puts the **description last** —
  where a reader that found a name by looking at the second cell of a row finds a quantity.
* **`slip`** has no table at all. Each position is a sentence, with different words and different
  separators from the synthetic corpus's own prose layout, and its labels follow their values
  instead of preceding them.

**Every value in the gold is printed**, the obligation `synth/render.py` carries and for the same
reason: a page a gold field cannot be read off makes the task unsolvable and the metric
meaningless. `tests/test_foreign_render.py` recovers all 22 of them through `pdfplumber`, exactly
as the synthetic renderer's own test does — this package would otherwise be measuring a page it had
quietly made incomplete, and every drop would read as a model failure.

Nothing here imports `synth/render.py`, `synth/pools.py` or `synth/overlay.py`, and a test asserts
it. The fonts are resolved from package data independently, because they are an asset of the
package rather than a decision of the synthetic renderer; sharing the *constant* would have been
harmless and sharing the module would not, and a rule with an exception in it is not checkable.

Rendering is deterministic for the reason M2 needs it to be: `rl_config.invariant` strips the
creation timestamp, so two renders of one document are byte-identical and a manifest of hashes
means something.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from doc_extract.foreign.dialect import BY_NAME, RATE_LABELS, Dialect
from doc_extract.schema.ksef import Invoice, LineItem
from doc_extract.synth.build import Context, Document

rl_config.invariant = 1

FONT_DIR = Path(str(resources.files("doc_extract").joinpath("assets", "fonts")))
REGULAR = "DejaVuSans"
BOLD = "DejaVuSans-Bold"

MARGIN = {"letterhead": 16.0, "statement": 18.0, "slip": 26.0}

#: Item-table columns in millimetres, in each dialect's own print order. Sized against the widest
#: value a column can ever hold rather than the widest this seed draws — a correction prints every
#: figure with a leading minus and one tier prints eight fractional digits, and a column that fits
#: the common case silently spills into its neighbour, where two figures fuse into one word with one
#: bounding box that word geometry cannot separate either.
#: The quantity column is the wide one, and it is wide for a reason worth recording: it holds the
#: quantity **and its unit** in one cell. At fifteen millimetres `10,968 mies.` was right-aligned
#: straight through the position column beside it, and `pdfplumber` returned `110,968` — a line
#: number fused to a quantity in one bounding box, which word geometry cannot separate either.
COLUMNS: dict[str, tuple[float, ...]] = {
    #: Poz. | Towar | Stawka | Ilość | Cena jedn. | Upust | Wartość netto | Podatek
    "letterhead": (11, 38, 21, 20, 29, 16, 21, 21),     # 177 of 178 mm
    #: Poz. | Ilość | Cena jedn. | Upust | Wartość netto | Stawka | Podatek | Towar
    #: The description column is 35 and not 34 because `wewnątrzwspólnotowa` is 34.3 mm at this
    #: size. A `Paragraph` one millimetre short of its longest word does not overrun — it splits the
    #: word across two lines, and the word stops being on the page.
    "statement": (11, 20, 29, 16, 21, 20, 21, 35),      # 173 of 174 mm
}

#: The column holding the description, per dialect. It wraps, and a `Paragraph` breaks a word too
#: long for its column mid-syllable rather than overrunning visibly — so a column too narrow does
#: not look wrong, it silently prints `wewnątrzwspól` and `notowa` as two words and the word is no
#: longer on the page at all.
DESCRIPTION_COLUMN = {"letterhead": 1, "statement": 7}

#: The column holding the rate label. It wraps for the opposite reason: `0 % eksport` is wider than
#: the figures the column is sized for, and as a flat string it would overrun rather than fold.
RATE_COLUMN = {"letterhead": 2, "statement": 5}

#: The columns drawn as wrapping paragraphs rather than as flat strings — derived from the two
#: above, so a dialect that moved one of them cannot leave this list describing the old position.
WRAPPED_COLUMNS: dict[str, tuple[int, ...]] = {
    template: (DESCRIPTION_COLUMN[template], RATE_COLUMN[template]) for template in COLUMNS
}

_TITLES = {"KOR": "title_correction", "ZAL": "title_advance"}


@dataclass(frozen=True, slots=True)
class Rendered:
    """The PDF and the one fact about it the manifest needs but the bytes do not readily give."""

    data: bytes
    pages: int


def render(document: Document) -> Rendered:
    """The document as a PDF, in whichever of the three foreign layouts it was assigned."""
    _register_fonts()
    speaker = BY_NAME[document.template]
    builder = {"letterhead": _letterhead, "statement": _statement, "slip": _slip}[document.template]
    margin = MARGIN[document.template] * mm

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

    doc.build(builder(document, speaker), canvasmaker=canvasmaker)
    return Rendered(data=buffer.value, pages=max((canvas.drawn for canvas in made), default=1))


# --------------------------------------------------------------------------- the three layouts


def _letterhead(document: Document, speaker: Dialect) -> list[Flowable]:
    """A corporate header, the parties side by side, and the rate summary above the payment."""
    invoice = document.invoice
    return [
        Paragraph(_title(invoice, speaker), _style("lh_title", size=16, font=BOLD)),
        Paragraph(
            f"{speaker.number}: <b>{escape(invoice.number)}</b>",
            _style("lh_no", size=10),
        ),
        Spacer(1, 2 * mm),
        _header_lines(document, speaker, align=TA_RIGHT),
        Spacer(1, 4 * mm),
        _party_boxes(document, speaker),
        Spacer(1, 5 * mm),
        _items_table(document, speaker),
        Spacer(1, 4 * mm),
        _summary_table(document, speaker, align="right"),
        Spacer(1, 4 * mm),
        *_payment(document, speaker),
        *_annotations(document, speaker),
    ]


def _statement(document: Document, speaker: Dialect) -> list[Flowable]:
    """The amount payable first, then what it is made of — the reverse of every other layout."""
    invoice = document.invoice
    return [
        Paragraph(
            f"{_title(invoice, speaker)} &mdash; {escape(invoice.number)}",
            _style("st_title", size=13, font=BOLD),
        ),
        Spacer(1, 3 * mm),
        *_payment(document, speaker),
        _summary_table(document, speaker, align="left"),
        Spacer(1, 4 * mm),
        _party_rows(document, speaker),
        Spacer(1, 3 * mm),
        _header_lines(document, speaker, align=None),
        Spacer(1, 4 * mm),
        _items_table(document, speaker),
        *_annotations(document, speaker),
    ]


def _slip(document: Document, speaker: Dialect) -> list[Flowable]:
    """No table: each position is a sentence, and each label follows the value it names."""
    invoice, context = document.invoice, document.context
    story: list[Flowable] = [
        Paragraph(_title(invoice, speaker), _style("sl_title", size=12, font=BOLD)),
        Paragraph(
            f"{escape(invoice.number)} &mdash; {speaker.number.lower()}",
            _style("sl_no", size=9),
        ),
        Spacer(1, 2 * mm),
    ]
    for label, value in _header_pairs(document, speaker):
        story.append(Paragraph(f"{escape(value)} &mdash; {escape(label.lower())}",
                               _style(f"sl_h{label}", size=8.5)))
    story.append(Spacer(1, 3 * mm))
    for role, party, company in _parties(document):
        story.append(Paragraph(
            f"{_party_text(party.name, party.nip, company, speaker)}<br/>"
            f"<i>{escape(role)}</i>",
            _style(f"sl_p{role}", size=9),
        ))
        story.append(Spacer(1, 2 * mm))
    for index, line in enumerate(invoice.lines):
        unit = _unit(context, index)
        story.append(Paragraph(
            f"{line.line_no}) {escape(line.description or '')}",
            _style(f"sl_d{index}", size=9),
        ))
        story.append(Paragraph(_position_text(line, unit, speaker), _style(f"sl_a{index}", size=8)))
    story += [
        Spacer(1, 3 * mm),
        _summary_table(document, speaker, align="left"),
        Spacer(1, 3 * mm),
        *_payment(document, speaker),
        *_annotations(document, speaker),
    ]
    return story


# --------------------------------------------------------------------------- shared blocks


def _header_pairs(document: Document, speaker: Dialect) -> list[tuple[str, str]]:
    """The header fields, as `(label, value)`. One list, so the three layouts cannot diverge.

    `number` is printed by each layout in its own place — beside the title, not in this block — so
    it is deliberately absent here rather than printed twice.
    """
    invoice, context = document.invoice, document.context
    pairs = [(speaker.issued, speaker.dates.format(invoice.issue_date))]
    if invoice.sale_date is not None:
        pairs.append((speaker.sold, speaker.dates.format(invoice.sale_date)))
    pairs.append((speaker.currency, invoice.currency))
    if context.corrected_number is not None:
        pairs.append((speaker.corrected, context.corrected_number))
        pairs.append((speaker.corrected_on, speaker.dates.format(context.corrected_date)))
    return pairs


def _header_lines(document: Document, speaker: Dialect, *, align) -> Flowable:
    text = "<br/>".join(
        f"{escape(label)}: <b>{escape(value)}</b>"
        for label, value in _header_pairs(document, speaker)
    )
    return Paragraph(text, _style(f"hdr{align}", size=9, align=align))


def _parties(document: Document) -> list[tuple[str, object, object]]:
    return [
        ("seller", document.invoice.seller, document.context.seller),
        ("buyer", document.invoice.buyer, document.context.buyer),
    ]


def _party_boxes(document: Document, speaker: Dialect) -> Flowable:
    """The two parties side by side in ruled boxes — a shape the synthetic corpus never draws."""
    invoice, context = document.invoice, document.context
    width = (210 - 2 * MARGIN["letterhead"]) * mm / 2
    cells = [[
        Paragraph(
            f"<b>{escape(speaker.seller)}</b><br/>"
            f"{_party_text(invoice.seller.name, invoice.seller.nip, context.seller, speaker)}",
            _style("lh_ps", size=9),
        ),
        Paragraph(
            f"<b>{escape(speaker.buyer)}</b><br/>"
            f"{_party_text(invoice.buyer.name, invoice.buyer.nip, context.buyer, speaker)}",
            _style("lh_pb", size=9),
        ),
    ]]
    table = Table(cells, colWidths=(width - 2 * mm, width - 2 * mm), hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (0, 0), 0.5, colors.black),
        ("BOX", (1, 0), (1, 0), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _party_rows(document: Document, speaker: Dialect) -> Flowable:
    """The parties stacked, with the label to the *right* of the block it names."""
    rows = [
        [Paragraph(_party_text(party.name, party.nip, company, speaker),
                   _style(f"st_p{role}", size=9)),
         Paragraph(f"<i>{escape(speaker.seller if role == 'seller' else speaker.buyer)}</i>",
                   _style(f"st_l{role}", size=9, align=TA_RIGHT))]
        for role, party, company in _parties(document)
    ]
    width = (210 - 2 * MARGIN["statement"]) * mm
    table = Table(rows, colWidths=(width * 0.72, width * 0.28), hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.grey),
    ]))
    return table


def _party_text(name: str, nip: str | None, company, speaker: Dialect) -> str:
    parts = [escape(name), escape(company.address_line)]
    if nip is not None:
        parts.append(f"{speaker.tax_id} {_nip(nip)}")
    return "<br/>".join(parts)


def _items_table(document: Document, speaker: Dialect) -> Flowable:
    """The rows, in this dialect's column order. `slip` never reaches here — it has no table."""
    invoice, context = document.invoice, document.context
    widths = tuple(width * mm for width in COLUMNS[speaker.name])
    header = [Paragraph(escape(text), _style(f"th{speaker.name}{index}", size=7, font=BOLD))
              for index, text in enumerate(speaker.columns)]
    rows = [header]
    for index, line in enumerate(invoice.lines):
        cells = _row_cells(line, _unit(context, index), speaker)
        rows.append([
            Paragraph(escape(cell), _style(f"td{speaker.name}{position}", size=7.5))
            if position in WRAPPED_COLUMNS[speaker.name] else cell
            for position, cell in enumerate(cells)
        ])

    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    numeric = _numeric_columns(speaker)
    style = [
        ("FONT", (0, 0), (-1, -1), REGULAR, 7.5),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.90, 0.90, 0.90)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    style += [("ALIGN", (column, 1), (column, -1), "RIGHT") for column in numeric]
    table.setStyle(TableStyle(style))
    return table


def _row_cells(line: LineItem, unit: str, speaker: Dialect) -> tuple[str, ...]:
    """One row's cells, in this dialect's order. The one place a column order is spelled out."""
    numbers = speaker.numbers
    position = str(line.line_no)
    description = line.description or ""
    rate = RATE_LABELS[line.vat_rate] if line.vat_rate else ""
    #: Quantity and unit share a cell. Real invoices print them together, and it is the kind of
    #: fusion a column reader has no rule for: the figure is no longer the whole of the cell.
    quantity = "" if line.quantity is None else f"{numbers.quantity(line.quantity)} {unit}"
    price = "" if line.unit_price_net is None else numbers.price(line.unit_price_net)
    #: An empty cell where there is no discount, because `P_10` is absent rather than zero. A
    #: printed `0,00` would put a figure in the gold's place that the gold does not carry.
    discount = "" if line.discount is None else numbers.amount(line.discount)
    net = "" if line.net is None else numbers.amount(line.net)
    vat = "" if line.vat is None else numbers.amount(line.vat)

    if speaker.name == "letterhead":
        return (position, description, rate, quantity, price, discount, net, vat)
    return (position, quantity, price, discount, net, rate, vat, description)


def _numeric_columns(speaker: Dialect) -> tuple[int, ...]:
    return (3, 4, 5, 6, 7) if speaker.name == "letterhead" else (1, 2, 3, 4, 6)


def _position_text(line: LineItem, unit: str, speaker: Dialect) -> str:
    """`slip`'s prose position: the same figures, different words, different separators."""
    numbers = speaker.numbers
    quantity = "" if line.quantity is None else numbers.quantity(line.quantity)
    price = "" if line.unit_price_net is None else numbers.price(line.unit_price_net)
    parts = [f"{quantity} {escape(unit)} po {price}"]
    if line.discount is not None:
        parts.append(f"upust {numbers.amount(line.discount)}")
    if line.net is not None:
        parts.append(f"netto {numbers.amount(line.net)}")
    if line.vat is not None:
        rate = RATE_LABELS[line.vat_rate] if line.vat_rate else ""
        parts.append(f"podatek {escape(rate)} {numbers.amount(line.vat)}")
    if line.net is not None and line.vat is not None:
        parts.append(f"brutto {numbers.amount(line.net + line.vat)}")
    return "; ".join(parts)


def _summary_table(document: Document, speaker: Dialect, *, align: str) -> Flowable:
    invoice = document.invoice
    numbers = speaker.numbers
    rows = [list(speaker.summary)]
    for total in invoice.rate_totals:
        rows.append([
            RATE_LABELS[total.rate],
            numbers.amount(total.net),
            numbers.amount(total.vat),
            numbers.amount(total.net + total.vat),
        ])
    rows.append([speaker.summary_total, "", "", numbers.amount(invoice.total_gross)])

    table = Table(rows, colWidths=(28 * mm, 26 * mm, 24 * mm, 26 * mm),
                  hAlign="RIGHT" if align == "right" else "LEFT")
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), BOLD, 7.5),
        ("FONT", (0, 1), (-1, -2), REGULAR, 8.5),
        ("FONT", (0, -1), (-1, -1), BOLD, 9.5),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]))
    return table


def _payment(document: Document, speaker: Dialect) -> list[Flowable]:
    invoice, context = document.invoice, document.context
    numbers = speaker.numbers
    lines = [
        f"{escape(speaker.payable)}: "
        f"<b>{numbers.amount(invoice.total_gross)} {escape(invoice.currency)}</b>",
        f"{escape(speaker.due)}: {speaker.dates.format(context.payment_due)}",
        f"{escape(speaker.payment_form)}: {escape(context.payment_form[1])}",
    ]
    if invoice.payment_account:
        lines.append(
            f"{escape(speaker.account)}: {_iban(invoice.payment_account)} "
            f"({escape(context.bank_name)})"
        )
    return [Paragraph("<br/>".join(lines), _style(f"pay{speaker.name}", size=9)), Spacer(1, 3 * mm)]


def _annotations(document: Document, speaker: Dialect) -> list[Flowable]:
    """What the page carries that the extraction schema deliberately does not model."""
    context, invoice = document.context, document.invoice
    notes: list[str] = []
    if context.annotations.split_payment:
        notes.append("mechanizm podzielonej płatności")
    if context.annotations.reverse_charge:
        notes.append("odwrotne obciążenie")
    if context.annotations.exempt:
        notes.append("dostawa zwolniona od podatku — art. 43 ust. 1 ustawy o VAT")
    if context.fx_rate is not None:
        notes.append(
            f"przelicznik NBP z {speaker.dates.format(context.fx_date)}: "
            f"1 {invoice.currency} = {speaker.numbers.amount(context.fx_rate, places=4)} PLN"
        )
    if context.correction_reason:
        notes.append(f"powód korekty: {context.correction_reason}")
    if context.gross_before_correction is not None:
        notes.append(f"wartość sprzed korekty: "
                     f"{speaker.numbers.amount(context.gross_before_correction)}")
    if context.order_value is not None:
        notes.append(f"kwota zamówienia: {speaker.numbers.amount(context.order_value)} "
                     f"{invoice.currency}")
    if not notes:
        return []
    return [Paragraph(
        f"{escape(speaker.notes)}: " + escape("; ".join(notes)),
        _style(f"notes{speaker.name}", size=8),
    )]


# --------------------------------------------------------------------------- small helpers


def _title(invoice: Invoice, speaker: Dialect) -> str:
    return escape(getattr(speaker, _TITLES.get(invoice.kind, "title_vat")))


def _unit(context: Context, index: int) -> str:
    return context.line_units[index] if index < len(context.line_units) else "szt."


def _nip(value: str) -> str:
    """`113 022 01 89` — spaced rather than dashed, which is the other half of real invoices."""
    return f"{value[:3]} {value[3:6]} {value[6:8]} {value[8:]}"


def _iban(value: str) -> str:
    """`PL 61109010140000071219812874` split after the country code and then in sixes.

    Deliberately not the groups of four the synthetic corpus prints: `eval/fields.py` compares an
    identifier with its separators removed, so any grouping scores the same — which makes this a
    free way to move the page without moving what a correct answer is.
    """
    body = value[2:]
    groups = " ".join(body[index:index + 6] for index in range(0, len(body), 6))
    return f"{value[:2]} {groups}"


def _style(name: str, *, size: float, font: str = REGULAR, align=None) -> ParagraphStyle:
    style = ParagraphStyle(name, fontName=font, fontSize=size, leading=size * 1.32)
    if align is not None:
        style.alignment = align
    return style


def _register_fonts() -> None:
    """DejaVu carries the Polish diacritics; the family reportlab ships with does not.

    Registration is global to reportlab and idempotent, so re-registering per render is cheap and
    keeps this module independent of whether anything else registered them first.
    """
    pdfmetrics.registerFont(TTFont(REGULAR, str(FONT_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(BOLD, str(FONT_DIR / "DejaVuSans-Bold.ttf")))


class _BytesTarget:
    """A file-like sink, so a render never touches the disk and a test never needs a path."""

    def __init__(self) -> None:
        self._chunks: list[bytes] = []

    def write(self, data: bytes) -> int:
        self._chunks.append(data)
        return len(data)

    @property
    def value(self) -> bytes:
        return b"".join(self._chunks)


class _PagedCanvas(Canvas):
    """A canvas that remembers how many pages it drew, which the manifest records."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.drawn = 0

    def showPage(self) -> None:
        self.drawn += 1
        super().showPage()
