"""Baseline B2: the page read by regular expressions and column positions, with no model at all.

**This baseline is allowed to cheat, and saying so is the point.** It knows `Numer faktury:`,
`Do zapłaty:` and `Stawka | Netto | VAT | Brutto` — the literal labels `synth/render.py` prints.
The extraction prompt is forbidden from knowing them (`tests/test_extract_prompt.py` asserts their
absence) precisely because a system fitted to the generator's own labels would close M7's
synthetic↔real gap in advance instead of measuring it. A *baseline* is the one place where that
fitting is legitimate, because its job is to be the strongest thing that is not a model: if an LLM
cannot beat a reader that was handed the answer key to the layout, that is worth knowing.

What it cannot be handed is the geometry problem. It reads the same tab-separated text the model
reads, so `3\t466,62` is two fields and `1 234,56` is one — `source/layout.py` did that work for
both of them, and neither gets it for free.

**Where it breaks is structural, not accidental.** Three failures are inherent to reading a table
by counting columns from the right:

* A row with a discount has one cell more than a row without, so quantity and unit price shift by a
  column and come back as the wrong figures. `P_10` is printed as an empty cell when absent — an
  empty cell leaves no trace in the text layer — and nothing in the row says which reading is right.
* A description that wrapped onto the lines above and below its numbers is not in the row at all,
  so most descriptions come back as a fragment or as nothing.
* Anything the three templates do not do, it does not read.

Those are the pattern baseline's honest score, and they are also useful: the shifted rows produce
values that are wrong while the totals stay right, which is exactly the kind of error M5's detector
has to be measured against.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from typing import Any

from doc_extract.source.document import CELL_BREAK

#: What the page prints for a rate -> the `TStawkaPodatku` code it means.
#:
#: A deliberate second copy of the renderer's own table, in the same spirit as the three rounding
#: helpers M2 keeps apart: if the baseline imported `render._RATE_LABELS` and inverted it, a label
#: printed wrongly would be read back wrongly and the two errors would cancel. Here a change to
#: either side is a visible disagreement.
RATE_LABELS: dict[str, str] = {
    "23%": "23", "8%": "8", "5%": "5", "0%": "0 KR", "0% WDT": "0 WDT", "0% eksport": "0 EX",
    "zw.": "zw", "o.o.": "oo", "np (I)": "np I", "np (II)": "np II",
}

#: The document titles the standard's three most common kinds are printed under.
KIND_LABELS: dict[str, str] = {"korygująca": "KOR", "zaliczkowa": "ZAL"}

#: How many value cells a table row ends with: quantity, unit price, net, rate, VAT.
_TRAILING_VALUES = 5

_TITLE = re.compile(r"^Faktura(?:\s+(\w+))?\s+nr\s+(.+)$")
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_AMOUNT = re.compile(r"-?\d[\d\u00a0 ]*(?:,\d+)?$")
_NIP = re.compile(r"NIP[:\s]\s*([\d\s-]{10,})")
_TO_PAY = re.compile(r"Do zapłaty:\s*(-?[\d\u00a0 ]*\d(?:,\d{2})?)\s+([A-Z]{3})")
_ACCOUNT = re.compile(r"Rachunek:\s*([A-Z]{2}[\d\u00a0 ]+\d)")
_SALE_DATE = re.compile(r"Data sprzedaży:\s*(\d{4}-\d{2}-\d{2})")
_POSITION_HEAD = re.compile(r"^(\d+)\.\s+(.+)$")
_POSITION_BODY = re.compile(
    r"^(?P<quantity>-?[\d\u00a0 ]*[\d,]+)\s+(?P<unit>\S+)\s+×\s+(?P<price>[\d\u00a0 ,]+?)"
    r"(?:\s+\(rabat\s+(?P<discount>[\d\u00a0 ,]+)\))?\s+=\s+"
    r"netto\s+(?P<net>-?[\d\u00a0 ,]+),\s+VAT\s+(?P<rate>.+?)\s+(?P<vat>-?[\d\u00a0 ,]+),\s+brutto"
)

_TOTALS_HEADER = ("Stawka", "Netto", "VAT", "Brutto")
#: Rows that end a party block: the next section, whatever it is.
_SECTION = frozenset({"Sprzedawca", "Nabywca", "Pozycje", "Lp.", "Stawka", "Adnotacje"})

Row = tuple[str, ...]


def read(text: str) -> dict[str, Any]:
    """A page as the wire shape, with `None` wherever no pattern matched.

    Never raises and never guesses at a value it did not find: an unmatched required field arrives
    at `Invoice` as `None` and is rejected there, which the pipeline records as `schema_invalid`.
    A baseline that filled in a plausible default would be scored on the default.
    """
    rows = _rows(text)
    kind, number = _title(rows)
    seller, buyer = _parties(rows)
    total_gross, currency = _to_pay(text)

    return {
        "kind": kind,
        "number": _cell_after(rows, "Numer faktury:") or number,
        "issue_date": _issue_date(rows, text),
        "sale_date": _sale_date(rows, text),
        "currency": _cell_after(rows, "Waluta:") or currency,
        "seller": seller,
        "buyer": buyer,
        "lines": _lines(rows),
        "rate_totals": _rate_totals(rows),
        "total_gross": total_gross,
        "payment_account": _account(text),
    }


def _rows(text: str) -> tuple[Row, ...]:
    return tuple(
        tuple(cell.strip() for cell in line.split(CELL_BREAK))
        for line in text.splitlines()
        if line.strip()
    )


def _title(rows: Sequence[Row]) -> tuple[str, str | None]:
    """The kind and the number from the document's own heading.

    `VAT` when no qualifier is printed, because that is what the standard's default document is —
    not a guess about this corpus. A page with no title at all yields no number, and the schema
    rejects the result rather than this function inventing one.
    """
    for index, _ in _titled(rows):
        match = _TITLE.match(rows[index][0])
        if match is not None:
            return KIND_LABELS.get(match.group(1) or "", "VAT"), match.group(2).strip()
    return "VAT", None


def _titled(rows: Sequence[Row]) -> Iterator[tuple[int, Row]]:
    for index, row in enumerate(rows):
        if len(row) == 1 and row[0].startswith("Faktura"):
            yield index, row


def _title_index(rows: Sequence[Row]) -> int | None:
    return next((index for index, _ in _titled(rows)), None)


def _cell_after(rows: Sequence[Row], label: str) -> str | None:
    """The second cell of the row whose first cell is `label` — a two-column metadata table."""
    for row in rows:
        if len(row) >= 2 and row[0] == label:
            return row[1] or None
    return None


def _issue_date(rows: Sequence[Row], text: str) -> str | None:
    labelled = _cell_after(rows, "Data wystawienia:")
    if labelled is not None:
        return labelled
    #: The compact layout prints `Wystawiono: <place>, <date>` as prose instead of a table row.
    for row in rows:
        if len(row) == 1 and row[0].startswith("Wystawiono:"):
            match = _DATE.search(row[0])
            if match is not None:
                return match.group(1)
    match = _DATE.search(text)
    return match.group(1) if match is not None else None


def _sale_date(rows: Sequence[Row], text: str) -> str | None:
    labelled = _cell_after(rows, "Data sprzedaży:")
    if labelled is not None:
        return labelled
    match = _SALE_DATE.search(text)
    return match.group(1) if match is not None else None


def _to_pay(text: str) -> tuple[str | None, str | None]:
    """The gross total and the currency, from the one line every layout prints them on together."""
    match = _TO_PAY.search(text)
    if match is None:
        return None, None
    return _amount(match.group(1)), match.group(2)


def _account(text: str) -> str | None:
    match = _ACCOUNT.search(text)
    return None if match is None else re.sub(r"\s+", "", match.group(1))


# --------------------------------------------------------------------------- parties


def _parties(rows: Sequence[Row]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Seller and buyer, however the layout at hand chose to arrange them.

    Three arrangements, tried in order, because the templates genuinely differ: side by side in one
    two-column block, one after the other under their own headings, or the seller as an unlabelled
    letterhead above the title with only the buyer named. The third is why a heading cannot simply
    be required — a real letterhead does not say `Sprzedawca` either.
    """
    columns = _column_block(rows)
    if columns is not None:
        return _party(columns[0]), _party(columns[1])

    labelled = _labelled_block(rows, "Sprzedawca")
    buyer = _labelled_block(rows, "Nabywca") or ()
    if labelled:
        return _party(labelled), _party(buyer)
    return _party(_letterhead(rows)), _party(buyer)


def _column_block(rows: Sequence[Row]) -> tuple[list[str], list[str]] | None:
    for index, row in enumerate(rows):
        if len(row) == 2 and row[0] == "Sprzedawca" and row[1] == "Nabywca":
            left: list[str] = []
            right: list[str] = []
            for following in rows[index + 1:]:
                if len(following) != 2:
                    break
                left.append(following[0])
                right.append(following[1])
            return left, right
    return None


def _labelled_block(rows: Sequence[Row], label: str) -> tuple[str, ...]:
    for index, row in enumerate(rows):
        if len(row) == 1 and row[0] == label:
            return tuple(_until_section(rows[index + 1:]))
    return ()


def _letterhead(rows: Sequence[Row]) -> tuple[str, ...]:
    """The single-cell lines above the title: a seller printed as a letterhead, with no heading."""
    end = _title_index(rows)
    return () if end is None else tuple(_until_section(rows[:end]))


def _until_section(rows: Sequence[Row]) -> Iterator[str]:
    for row in rows:
        if len(row) != 1 or row[0] in _SECTION or row[0].startswith("Faktura"):
            return
        yield row[0]


def _party(lines: Sequence[str]) -> dict[str, Any]:
    """A block of address lines split into the three fields the schema carries.

    The address is rejoined with `", "` — the separator `pools.Company.address_line` uses — because
    a street and a postcode printed on two lines are one address, and the gold holds it as one
    string. This is the baseline reading the corpus's own convention, which is what a baseline
    fitted to the corpus is for.
    """
    nip: str | None = None
    remaining: list[str] = []
    for line in lines:
        match = _NIP.search(line)
        if match is not None and nip is None:
            nip = re.sub(r"\D", "", match.group(1))
        else:
            remaining.append(line)

    name = remaining[0] if remaining else None
    address = ", ".join(remaining[1:]) or None
    return {"name": name, "nip": nip, "address": address}


# --------------------------------------------------------------------------- the two tables


def _rate_totals(rows: Sequence[Row]) -> list[dict[str, Any]]:
    """The summary block: every row under the rate header whose first cell is a rate label."""
    totals: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if tuple(row[:4]) != _TOTALS_HEADER:
            continue
        for following in rows[index + 1:]:
            code = RATE_LABELS.get(following[0]) if following else None
            if code is None or len(following) < 3:
                break
            totals.append({
                "rate": code, "net": _amount(following[1]), "vat": _amount(following[2])
            })
        break
    return totals


def _lines(rows: Sequence[Row]) -> list[dict[str, Any]]:
    """Item rows, from a table when there is one and from prose when there is not."""
    return _table_lines(rows) or _prose_lines(rows)


def _table_lines(rows: Sequence[Row]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        if len(row) < _TRAILING_VALUES + 1 or not row[0].isdigit():
            continue
        quantity, price, net, rate, vat = row[-_TRAILING_VALUES:]
        code = RATE_LABELS.get(rate)
        if code is None or not _AMOUNT.match(net):
            continue
        middle = row[1:-_TRAILING_VALUES]
        items.append({
            "line_no": int(row[0]),
            #: The last middle cell is the unit, which the schema does not carry; anything before
            #: it is whatever fragment of the description landed on the same line as the numbers.
            "description": " ".join(middle[:-1]) or None,
            "quantity": _amount(quantity),
            "unit_price_net": _amount(price),
            "discount": None,
            "net": _amount(net),
            "vat": _amount(vat),
            "vat_rate": code,
        })
    return items


def _prose_lines(rows: Sequence[Row]) -> list[dict[str, Any]]:
    """The compact layout, where a position is two sentences rather than a row of cells."""
    items: list[dict[str, Any]] = []
    pending: tuple[int, str] | None = None
    for row in rows:
        if len(row) != 1:
            continue
        head = _POSITION_HEAD.match(row[0])
        if head is not None:
            pending = (int(head.group(1)), head.group(2))
            continue
        body = _POSITION_BODY.match(row[0])
        if body is None or pending is None:
            continue
        line_no, description = pending
        pending = None
        code = RATE_LABELS.get(body.group("rate").strip())
        if code is None:
            continue
        items.append({
            "line_no": line_no,
            "description": description,
            "quantity": _amount(body.group("quantity")),
            "unit_price_net": _amount(body.group("price")),
            "discount": _amount(body.group("discount")),
            "net": _amount(body.group("net")),
            "vat": _amount(body.group("vat")),
            "vat_rate": code,
        })
    return items


def _amount(printed: str | None) -> str | None:
    """`1 234,56` back to `1234.56`, the wire format's exact decimal string.

    Undoing the Polish convention is the whole of what a numeric field needs, and it is done here
    rather than by `Invoice`, because the schema's contract is that money arrives already
    normalised — the model is asked for the same thing in the same words.
    """
    if printed is None:
        return None
    text = printed.replace("\u00a0", "").replace(" ", "").replace(",", ".")
    return text or None
