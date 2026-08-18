"""Check digits: known-good values, single-digit corruption, transposition, and malformed input.

The valid values here were computed independently of the module under test. The invalid ones are
the realistic failure modes of extraction — one wrong digit and a swapped pair — not random noise.
"""

from __future__ import annotations

import pytest

from doc_extract.schema.checksums import (
    is_valid_iban,
    is_valid_nip,
    is_valid_regon,
    strip_separators,
)

VALID_NIPS = ("1130220189", "5221234561", "9998887778")
VALID_IBAN = "PL61109010140000071219812874"


@pytest.mark.parametrize("nip", VALID_NIPS)
def test_valid_nip(nip):
    assert is_valid_nip(nip)


@pytest.mark.parametrize("nip", VALID_NIPS)
def test_nip_survives_the_formatting_humans_and_ocr_add(nip):
    spaced = f"{nip[:3]}-{nip[3:5]}-{nip[5:7]}-{nip[7:]}"
    assert is_valid_nip(spaced)
    assert is_valid_nip(f"PL {nip}")
    assert is_valid_nip(f"  {nip}  ")


def test_nip_rejects_a_wrong_check_digit():
    assert not is_valid_nip("1130220180")


def test_nip_rejects_a_transposition():
    """Two swapped digits are the classic extraction error; different weights catch them."""
    assert not is_valid_nip("1130220819")


@pytest.mark.parametrize("bad", ["", "113022018", "11302201899", "abcdefghij", "113022018X"])
def test_nip_rejects_malformed_input(bad):
    assert not is_valid_nip(bad)


def test_regon_9_and_14():
    assert is_valid_regon("123456785")
    assert is_valid_regon("12345678512347")


def test_regon_14_requires_both_check_digits():
    """The composite form embeds a valid 9-digit REGON; breaking either half must fail."""
    assert not is_valid_regon("12345678612347")  # embedded 9-digit REGON corrupted
    assert not is_valid_regon("12345678512348")  # 14-digit check digit corrupted


@pytest.mark.parametrize("bad", ["", "12345678", "1234567850", "1234567851234"])
def test_regon_rejects_wrong_lengths_and_digits(bad):
    assert not is_valid_regon(bad)


def test_valid_iban():
    assert is_valid_iban(VALID_IBAN)
    assert is_valid_iban(VALID_IBAN, country="PL")
    assert is_valid_iban("PL 61 1090 1014 0000 0712 1981 2874")


def test_iban_rejects_a_corrupted_digit():
    assert not is_valid_iban(VALID_IBAN[:-1] + "5")


def test_iban_country_pin_rejects_a_foreign_account():
    """A valid German IBAN is still wrong in a field that must hold a Polish account."""
    de = "DE89370400440532013000"
    assert is_valid_iban(de)
    assert not is_valid_iban(de, country="PL")


def test_bare_nrb_without_the_country_prefix_is_rejected():
    """Polish accounts are printed as a 26-digit NRB too; that form carries no country code."""
    assert not is_valid_iban(VALID_IBAN[2:], country="PL")


@pytest.mark.parametrize("bad", ["", "PL", "PLXX1090", "1234"])
def test_iban_rejects_malformed_input(bad):
    assert not is_valid_iban(bad)


def test_strip_separators_leaves_alphanumerics():
    assert strip_separators(" 113-022 01.89 ") == "1130220189"


#: A NIP whose digits are fullwidth forms. `str.isdecimal()` accepts them and `int()` converts
#: them, so the check digit used to pass on a string that equals no NIP ever printed on a page.
_FULLWIDTH = str.maketrans({str(n): chr(0xFF10 + n) for n in range(10)})


def test_the_country_pin_is_applied_however_the_country_is_cased():
    """`country="pl"` passed the prefix check and then skipped the length check entirely.

    The prefix was compared case-insensitively while the length was pinned against a literal
    `"PL"`, so a lowercase argument quietly bought a weaker check than the caller asked for. The
    value below is a valid mod-97 IBAN of the wrong length for Poland.
    """
    wrong_length = "PL57370400440532013000"
    assert is_valid_iban(wrong_length)
    assert not is_valid_iban(wrong_length, country="PL")
    assert not is_valid_iban(wrong_length, country="pl")
    assert is_valid_iban(VALID_IBAN, country="pl")


def test_a_fullwidth_digit_does_not_pass_a_check_digit():
    """An identifier that validates but compares unequal to the printed one is the worse failure.

    The detector would report it clean while the extracted value was wrong — precisely the case
    these functions exist to catch. `_SEPARATORS` already treats look-alike codepoints as a hazard;
    the digit classes now do too.
    """
    for value in VALID_NIPS:
        assert is_valid_nip(value)
        assert not is_valid_nip(value.translate(_FULLWIDTH))
    assert not is_valid_regon("123456785".translate(_FULLWIDTH))
    assert not is_valid_iban(VALID_IBAN.translate(_FULLWIDTH), country="PL")
