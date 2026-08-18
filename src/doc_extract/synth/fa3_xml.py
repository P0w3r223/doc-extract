"""The generated invoice as a KSeF FA(3) document, and the same document read back as gold.

Ground truth and the rendered page come from **one artifact**, which is the whole reason the corpus
is generated rather than scraped: there is no annotation step to be noisy, and no way for the label
to disagree with the document except through a bug this module's round-trip test would catch.

`to_xml` writes a document that validates against the vendored XSD — `tests/test_synth_xml.py`
checks every tier against the real schema, offline. `gold_from_xml` reads one back into the
`Invoice` subset. The two are required to compose to the identity, so a corpus whose XML says one
thing and whose gold says another is a red test rather than a silent wrong label.

**One deliberate restriction.** FA(3) folds pairs of rates into a single block: `P_13_1` carries
the standard rate whether that rate is 23 % or the historical 22 %, and `P_13_2` likewise merges
8 % with 7 %. A document written into those blocks therefore cannot say which of the pair it meant,
so the round-trip could not be exact. The generator refuses to emit the historical members, and
`to_xml` raises rather than writing a rate it could not read back — an exception here is a corpus
that never gets built, which is much cheaper than gold that is quietly wrong.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Final
from xml.etree import ElementTree as ET

from doc_extract.schema.ksef import Invoice, LineItem, Party, RateTotal
from doc_extract.synth.build import Document
from doc_extract.synth.rate_slots import AMBIGUOUS, FA_ORDER, SLOT_TO_RATE, SLOTS

NS: Final = "http://crd.gov.pl/wzor/2025/06/25/13775/"
_Q: Final = f"{{{NS}}}"

#: Serialise the structure without a prefix, as the Ministry's own examples do. This has to be a
#: registration rather than `tostring(default_namespace=...)`, because `KodFormularza` carries two
#: unqualified attributes and that option refuses to write any.
ET.register_namespace("", NS)


# --------------------------------------------------------------------------- writing


def to_xml(document: Document) -> str:
    """The document as FA(3), indented — meant to be read by a human as well as by a parser."""
    invoice = document.invoice
    root = ET.Element(f"{_Q}Faktura")
    _naglowek(root, document)
    _podmiot1(root, invoice.seller, document)
    _podmiot2(root, invoice.buyer, document)
    _fa(root, document)

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _naglowek(parent: ET.Element, document: Document) -> None:
    node = _sub(parent, "Naglowek")
    code = _sub(node, "KodFormularza", "FA")
    code.set("kodSystemowy", "FA (3)")
    code.set("wersjaSchemy", "1-0E")
    _sub(node, "WariantFormularza", "3")
    _sub(node, "DataWytworzeniaFa", document.context.issued_at.isoformat(timespec="seconds") + "Z")
    _sub(node, "SystemInfo", "doc-extract synthetic corpus")


def _podmiot1(parent: ET.Element, seller: Party, document: Document) -> None:
    node = _sub(parent, "Podmiot1")
    identity = _sub(node, "DaneIdentyfikacyjne")
    _sub(identity, "NIP", seller.nip)
    _sub(identity, "Nazwa", seller.name)
    _address(node, document.context.seller)


def _podmiot2(parent: ET.Element, buyer: Party, document: Document) -> None:
    node = _sub(parent, "Podmiot2")
    identity = _sub(node, "DaneIdentyfikacyjne")
    if buyer.nip is not None:
        _sub(identity, "NIP", buyer.nip)
    else:
        _sub(identity, "BrakID", "1")
    _sub(identity, "Nazwa", buyer.name)
    _address(node, document.context.buyer)
    #: Both are mandatory and both mean "no": the buyer is neither a local-government unit nor a
    #: member of a VAT group.
    _sub(node, "JST", "2")
    _sub(node, "GV", "2")


def _address(parent: ET.Element, company) -> None:
    node = _sub(parent, "Adres")
    _sub(node, "KodKraju", "PL")
    _sub(node, "AdresL1", company.street)
    _sub(node, "AdresL2", f"{company.postcode} {company.city}")


def _fa(parent: ET.Element, document: Document) -> None:
    invoice, context = document.invoice, document.context
    node = _sub(parent, "Fa")
    _sub(node, "KodWaluty", invoice.currency)
    _sub(node, "P_1", invoice.issue_date.isoformat())
    _sub(node, "P_1M", context.place)
    _sub(node, "P_2", invoice.number)
    if invoice.sale_date is not None:
        _sub(node, "P_6", invoice.sale_date.isoformat())
    _rate_totals(node, invoice.rate_totals, context.vat_in_pln)
    _sub(node, "P_15", _money(invoice.total_gross))
    if context.fx_rate is not None:
        _sub(node, "KursWalutyZ", _plain(context.fx_rate))
    _adnotacje(node, document)
    _sub(node, "RodzajFaktury", invoice.kind)
    _korekta(node, document)
    for line, unit in zip(invoice.lines, context.line_units, strict=True):
        _wiersz(node, line, unit)
    _platnosc(node, document)


def _rate_totals(
    parent: ET.Element, totals: tuple[RateTotal, ...], vat_in_pln: tuple[Decimal, ...]
) -> None:
    """Written in the schema's own order, not the order the invoice happens to list them in."""
    written: dict[str, str] = {}
    for index, total in enumerate(totals):
        if total.rate in AMBIGUOUS:
            raise ValueError(
                f"rate {total.rate!r} shares a P_13 block with another code and could not be read "
                "back unambiguously; the generator does not emit it"
            )
        net_tag, vat_tag = SLOTS[total.rate]
        written[net_tag] = _money(total.net)
        if vat_tag is not None:
            written[vat_tag] = _money(total.vat)
            if vat_in_pln:
                written[f"{vat_tag}W"] = _money(vat_in_pln[index])
    for tag in FA_ORDER:
        if tag in written:
            _sub(parent, tag, written[tag])


def _adnotacje(parent: ET.Element, document: Document) -> None:
    flags = document.context.annotations
    node = _sub(parent, "Adnotacje")
    _sub(node, "P_16", _yes_no(flags.cash_basis))
    _sub(node, "P_17", _yes_no(flags.self_billing))
    _sub(node, "P_18", _yes_no(flags.reverse_charge))
    _sub(node, "P_18A", _yes_no(flags.split_payment))
    exemption = _sub(node, "Zwolnienie")
    if flags.exempt:
        _sub(exemption, "P_19", "1")
        _sub(exemption, "P_19C", "art. 43 ust. 1 ustawy o podatku od towarów i usług")
    else:
        _sub(exemption, "P_19N", "1")
    _sub(_sub(node, "NoweSrodkiTransportu"), "P_22N", "1")
    _sub(node, "P_23", "2")
    _sub(_sub(node, "PMarzy"), "P_PMarzyN", "1")


def _korekta(parent: ET.Element, document: Document) -> None:
    context = document.context
    if context.corrected_number is None:
        return
    _sub(parent, "PrzyczynaKorekty", context.correction_reason)
    _sub(parent, "TypKorekty", "2")
    corrected = _sub(parent, "DaneFaKorygowanej")
    _sub(corrected, "DataWystFaKorygowanej", context.corrected_date.isoformat())
    _sub(corrected, "NrFaKorygowanej", context.corrected_number)
    #: The corrected invoice predates this corpus, so it carries no KSeF number.
    _sub(corrected, "NrKSeFN", "1")
    if context.gross_before_correction is not None:
        _sub(parent, "P_15ZK", _money(context.gross_before_correction))


def _wiersz(parent: ET.Element, line: LineItem, unit: str) -> None:
    node = _sub(parent, "FaWiersz")
    _sub(node, "NrWierszaFa", str(line.line_no))
    _sub(node, "P_7", line.description)
    _sub(node, "P_8A", unit)
    _sub(node, "P_8B", _plain(line.quantity))
    _sub(node, "P_9A", _plain(line.unit_price_net))
    if line.discount is not None:
        _sub(node, "P_10", _money(line.discount))
    _sub(node, "P_11", _money(line.net))
    _sub(node, "P_11Vat", _money(line.vat))
    _sub(node, "P_12", line.vat_rate)


def _platnosc(parent: ET.Element, document: Document) -> None:
    invoice, context = document.invoice, document.context
    node = _sub(parent, "Platnosc")
    _sub(_sub(node, "TerminPlatnosci"), "Termin", context.payment_due.isoformat())
    _sub(node, "FormaPlatnosci", context.payment_form[0])
    if invoice.payment_account is not None:
        account = _sub(node, "RachunekBankowy")
        #: Stored as the full IBAN rather than the bare 26-digit NRB, because that is the form the
        #: mod-97 check applies to and therefore the form the gold has to carry.
        _sub(account, "NrRB", invoice.payment_account)
        _sub(account, "NazwaBanku", context.bank_name)


def _sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    node = ET.SubElement(parent, f"{_Q}{tag}")
    if text is not None:
        node.text = text
    return node


def _yes_no(flag: bool) -> str:
    """`TWybor1_2`: 1 is yes, 2 is no. The block is mandatory even when everything is no."""
    return "1" if flag else "2"


def _money(value: Decimal) -> str:
    """Two decimals always, and never a signed zero, which reads as an error to a human."""
    return f"{value + Decimal(0):.2f}"


def _plain(value: Decimal) -> str:
    """Positional notation: `str()` renders a small unit price as `4E-8`, which is no decimal."""
    return format(value, "f")


# --------------------------------------------------------------------------- reading back


def gold_from_xml(text: str) -> Invoice:
    """The FA(3) subset this project extracts, read out of a document it wrote.

    Only the subset is recovered. Everything in `Context` is present in the XML and deliberately
    ignored here — a field that is not modelled is a field no metric can accidentally score.
    """
    root = ET.fromstring(text)
    fa = root.find(f"{_Q}Fa")
    seller = root.find(f"{_Q}Podmiot1")
    buyer = root.find(f"{_Q}Podmiot2")
    sale_date = _text(fa, "P_6")
    account = fa.find(f"{_Q}Platnosc/{_Q}RachunekBankowy/{_Q}NrRB")

    return Invoice(
        kind=_text(fa, "RodzajFaktury"),
        number=_text(fa, "P_2"),
        issue_date=dt.date.fromisoformat(_text(fa, "P_1")),
        sale_date=dt.date.fromisoformat(sale_date) if sale_date is not None else None,
        currency=_text(fa, "KodWaluty"),
        seller=_party(seller),
        buyer=_party(buyer),
        lines=tuple(_line(node) for node in fa.findall(f"{_Q}FaWiersz")),
        rate_totals=_totals(fa),
        total_gross=Decimal(_text(fa, "P_15")),
        payment_account=account.text if account is not None else None,
    )


def _party(node: ET.Element) -> Party:
    identity = node.find(f"{_Q}DaneIdentyfikacyjne")
    address = node.find(f"{_Q}Adres")
    lines = [_text(address, "AdresL1"), _text(address, "AdresL2")] if address is not None else []
    return Party(
        name=_text(identity, "Nazwa"),
        nip=_text(identity, "NIP"),
        address=", ".join(part for part in lines if part) or None,
    )


def _line(node: ET.Element) -> LineItem:
    discount = _text(node, "P_10")
    return LineItem(
        line_no=int(_text(node, "NrWierszaFa")),
        description=_text(node, "P_7"),
        quantity=_optional_decimal(node, "P_8B"),
        unit_price_net=_optional_decimal(node, "P_9A"),
        discount=Decimal(discount) if discount is not None else None,
        net=_optional_decimal(node, "P_11"),
        vat=_optional_decimal(node, "P_11Vat"),
        vat_rate=_text(node, "P_12"),
    )


def _totals(fa: ET.Element) -> tuple[RateTotal, ...]:
    totals = []
    for tag in FA_ORDER:
        if tag not in SLOT_TO_RATE:
            continue
        net = _text(fa, tag)
        if net is None:
            continue
        rate = SLOT_TO_RATE[tag]
        vat_tag = SLOTS[rate][1]
        vat = _text(fa, vat_tag) if vat_tag is not None else None
        totals.append(RateTotal(rate=rate, net=Decimal(net), vat=Decimal(vat or "0.00")))
    return tuple(totals)


def _text(parent: ET.Element, tag: str) -> str | None:
    node = parent.find(f"{_Q}{tag}")
    return node.text if node is not None else None


def _optional_decimal(parent: ET.Element, tag: str) -> Decimal | None:
    value = _text(parent, tag)
    return Decimal(value) if value is not None else None
