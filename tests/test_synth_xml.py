"""The generated documents are valid FA(3), and reading one back gives exactly the gold.

Both halves matter for a different reason.

**Validation** is what makes "KSeF-conformant" a checkable claim rather than a README sentence. It
runs against the vendored schema with remote fetching disabled, so a green test cannot mean the
Ministry's server answered.

**The round-trip** is what makes the gold trustworthy. Generation and ground truth come from one
artifact; if writing and reading disagreed anywhere, the corpus would carry labels that do not
describe its own documents — the exact failure mode a scraped corpus has and this one exists to
avoid.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from decimal import Decimal

import pytest

from doc_extract.schema.ksef import Invoice, Party, RateTotal
from doc_extract.synth import fa3_xml
from doc_extract.synth.build import build
from doc_extract.synth.corpus import documents
from doc_extract.synth.rate_slots import AMBIGUOUS, SLOTS
from doc_extract.synth.tiers import TIERS, Tier

PER_TIER = 4


@pytest.fixture(scope="module")
def corpus():
    return list(documents(per_tier=PER_TIER))


@pytest.mark.parametrize("tier", TIERS, ids=lambda tier: tier.name)
def test_every_tier_validates_against_the_vendored_schema(tier: Tier, fa3_schema):
    for index in range(PER_TIER):
        document = build(tier, seed=9_000 + index,
                         doc_id=f"{tier.name}-{index}", template="classic")
        fa3_schema.validate(fa3_xml.to_xml(document))


def test_the_schema_is_compiled_without_touching_the_network(fa3_schema):
    """`allow="local"` is set in the fixture; this pins that it stayed set."""
    assert fa3_schema.source.allow == "local"


def test_reading_a_document_back_gives_the_invoice_it_was_written_from(corpus):
    for document in corpus:
        assert fa3_xml.gold_from_xml(fa3_xml.to_xml(document)) == document.invoice, document.doc_id


def test_rate_totals_come_back_in_the_order_the_standard_lists_them(corpus):
    """The document can only state one order, so the gold has to agree with the document."""
    for document in corpus:
        rates = [total.rate for total in document.invoice.rate_totals]
        positions = [fa3_xml.FA_ORDER.index(SLOTS[rate][0]) for rate in rates]
        assert positions == sorted(positions), document.doc_id


def test_the_header_pins_the_schema_version(corpus):
    """A document that did not say which structure it follows would date badly and silently."""
    xml = fa3_xml.to_xml(corpus[0])
    assert 'kodSystemowy="FA (3)"' in xml
    assert 'wersjaSchemy="1-0E"' in xml


def test_untaxed_rates_are_written_with_no_tax_element(corpus, fa3_schema):
    """`zw` and `oo` have a net block and no `P_14_x` at all; inventing one would be invalid."""
    exempt = next(doc for doc in corpus if any(t.rate == "zw" for t in doc.invoice.rate_totals))
    xml = fa3_xml.to_xml(exempt)
    assert "<P_13_7>" in xml
    fa3_schema.validate(xml)


def test_an_eight_decimal_price_survives_the_round_trip(corpus):
    """`str()` would render a small `TKwotowy2` as `4E-8`, which is not a decimal at all."""
    rounding = next(doc for doc in corpus if doc.tier == "grosz_rounding")
    back = fa3_xml.gold_from_xml(fa3_xml.to_xml(rounding))
    for written, read in zip(rounding.invoice.lines, back.lines, strict=True):
        assert written.unit_price_net == read.unit_price_net
    assert "E-" not in fa3_xml.to_xml(rounding)


def test_a_rate_that_could_not_be_read_back_is_refused():
    """FA(3) merges 22 % into the 23 % block. Writing it would produce gold that is a guess."""
    document = build(TIERS[0], seed=11, doc_id="x", template="classic")
    ambiguous = document.invoice.model_copy(
        update={"rate_totals": (RateTotal(rate="22", net=Decimal("100.00"), vat=Decimal("22.00")),)}
    )
    with pytest.raises(ValueError, match="shares a P_13 block"):
        fa3_xml.to_xml(replace(document, invoice=ambiguous))


def test_no_ambiguous_rate_has_a_slot_of_its_own():
    """If one ever did, the refusal above would be wrong rather than merely cautious."""
    assert AMBIGUOUS.isdisjoint(SLOTS)


def test_a_buyer_without_a_nip_is_written_as_such(corpus):
    """FA(3) admits a consumer with no identifier; the document has to say so explicitly."""
    document = corpus[0]
    consumer = document.invoice.model_copy(
        update={"buyer": Party(name="Jan Kowalski", nip=None)}
    )
    xml = fa3_xml.to_xml(replace(document, invoice=consumer))
    assert "<BrakID>1</BrakID>" in xml
    assert fa3_xml.gold_from_xml(xml).buyer.nip is None


def test_correction_documents_reference_the_invoice_they_correct(corpus, fa3_schema):
    correction = next(doc for doc in corpus if doc.tier == "correction")
    xml = fa3_xml.to_xml(correction)
    assert correction.context.corrected_number in xml
    assert "<P_15ZK>" in xml
    fa3_schema.validate(xml)


def test_the_gold_reader_returns_only_the_subset(corpus):
    """A field nobody decided to measure must not reach the gold, however clearly the XML states it.

    The place of issue, the payment term and the exchange rate are all in the document and all
    outside `Invoice`; `extra="forbid"` would reject them, so this asserts the reader never tries.
    """
    document = corpus[0]
    gold = fa3_xml.gold_from_xml(fa3_xml.to_xml(document))
    assert isinstance(gold, Invoice)
    assert document.context.place not in repr(gold)


def test_dates_survive_as_dates(corpus):
    for document in corpus:
        gold = fa3_xml.gold_from_xml(fa3_xml.to_xml(document))
        assert isinstance(gold.issue_date, dt.date)
        assert gold.issue_date == document.invoice.issue_date
        assert gold.sale_date == document.invoice.sale_date
