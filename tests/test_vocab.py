"""The closed domains must match the vendored XSD exactly — drift is a red test, not a surprise.

`vocab.py` is generated from `schemas/fa3.xsd`. If the Ministry republishes the structure and the
XSD is re-vendored without regenerating, these tests fail, which is the whole point: the constants
claim to mirror a national standard and must not be allowed to quietly stop doing so.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

import pytest

from doc_extract.schema import vocab

XSD_PATH = Path(__file__).resolve().parents[1] / "schemas" / "fa3.xsd"
XS = "{http://www.w3.org/2001/XMLSchema}"


@pytest.fixture(scope="module")
def schema() -> ElementTree.Element:
    """Parsing also proves the vendored file is well-formed XML."""
    return ElementTree.parse(XSD_PATH).getroot()


def enumeration(schema: ElementTree.Element, type_name: str) -> set[str]:
    for node in schema.iter(f"{XS}simpleType"):
        if node.get("name") == type_name:
            return {e.get("value") for e in node.iter(f"{XS}enumeration")}
    raise AssertionError(f"simpleType {type_name!r} not found in the vendored XSD")


def test_currencies_match_the_schema(schema):
    assert enumeration(schema, "TKodWaluty") == vocab.CURRENCIES


def test_invoice_kinds_match_the_schema(schema):
    assert enumeration(schema, "TRodzajFaktury") == vocab.INVOICE_KINDS


def test_vat_rate_codes_match_the_schema(schema):
    assert enumeration(schema, "TStawkaPodatku") == vocab.VAT_RATE_CODES


def test_vendored_schema_is_the_documented_version(schema):
    """Pin the file to FA(3) 1-0E, so a re-vendor of a different version cannot pass silently."""
    fixed = {
        attr.get("name"): attr.get("fixed")
        for attr in schema.iter(f"{XS}attribute")
        if attr.get("fixed")
    }
    assert fixed.get("kodSystemowy") == "FA (3)"
    assert fixed.get("wersjaSchemy") == "1-0E"


def test_correction_kinds_are_a_subset_of_invoice_kinds():
    assert vocab.CORRECTION_KINDS <= vocab.INVOICE_KINDS


def test_untaxed_codes_are_a_subset_of_the_rate_codes():
    assert vocab.UNTAXED_RATE_CODES <= vocab.VAT_RATE_CODES


def test_every_rate_code_has_a_fraction():
    """No rate may be silently unpriced — the VAT invariant looks every code up by name."""
    assert set(vocab.RATE_FRACTION) == set(vocab.VAT_RATE_CODES)


def test_untaxed_codes_carry_a_zero_fraction():
    assert all(vocab.RATE_FRACTION[code] == 0 for code in vocab.UNTAXED_RATE_CODES)


def test_taxed_fractions_are_exact_decimals():
    """Decimal, never float: 0.23 as a float would not round-trip against a two-decimal amount."""
    assert str(vocab.RATE_FRACTION["23"]) == "0.23"
    assert str(vocab.RATE_FRACTION["8"]) == "0.08"
