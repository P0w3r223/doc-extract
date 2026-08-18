"""Check digits carried by Polish identifiers: NIP, REGON, and IBAN.

These are the cheapest error detectors an invoice offers. They need no gold labels, no model and
no reference data — a transposed pair of digits in an extracted NIP fails arithmetic that the
issuer already performed. Every function is total: malformed input returns ``False`` rather than
raising, because the caller is inspecting a value an extractor produced and must be able to record
"this is wrong" as data.

What they do *not* do: prove the identifier exists or belongs to the named party. A checksum rules
out corruption, not fabrication. That limit is stated here so no metric downstream is read as more
than it is.
"""

from __future__ import annotations

import string
from typing import Final

_NIP_WEIGHTS: Final = (6, 5, 7, 2, 3, 4, 5, 6, 7)
_REGON_9_WEIGHTS: Final = (8, 9, 2, 3, 4, 5, 6, 7)
_REGON_14_WEIGHTS: Final = (2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8)

#: Written as codepoints on purpose. OCR routinely emits an en dash, em dash, non-breaking
#: space or true minus sign where the printed page has a plain hyphen or space; as literals
#: these are indistinguishable from their ASCII neighbours in an editor, a diff or a review.
_SEPARATORS: Final = frozenset(
    " .-"
    + chr(0x09)     # tab
    + chr(0x2013)   # en dash
    + chr(0x2014)   # em dash
    + chr(0x00A0)   # no-break space
    + chr(0x2212)   # minus sign
)


#: ASCII only, and checked as membership rather than through `str.isdecimal` / `str.isalnum`.
#: Those predicates accept fullwidth (U+FF10..U+FF19) and Arabic-Indic digits, which `int()` then
#: happily converts — so a NIP written in them passed the check digit while comparing unequal to
#: every NIP ever printed on a page. This module already treats look-alike codepoints as the hazard
#: they are (see `_SEPARATORS`); admitting them here would contradict that where it matters most.
_DIGITS: Final = frozenset(string.digits)
_ASCII_UPPER: Final = frozenset(string.ascii_uppercase)
_IBAN_BODY: Final = _DIGITS | _ASCII_UPPER


def strip_separators(value: str) -> str:
    """Drop the spaces, hyphens and dots humans and OCR sprinkle through identifiers."""
    return "".join(ch for ch in value if ch not in _SEPARATORS)


def _digits(value: str, length: int) -> list[int] | None:
    cleaned = strip_separators(value)
    if len(cleaned) != length or not _DIGITS.issuperset(cleaned):
        return None
    return [int(ch) for ch in cleaned]


def _weighted_mod_11(digits: list[int], weights: tuple[int, ...]) -> int:
    return sum(d * w for d, w in zip(digits, weights, strict=True)) % 11


def is_valid_nip(value: str) -> bool:
    """Ten digits, weighted mod 11. A remainder of 10 belongs to no valid NIP.

    Accepts an optional ``PL`` prefix, which the FA(3) structure carries separately as
    ``PrefiksPodatnika`` but which appears inline on the printed page.
    """
    cleaned = strip_separators(value).upper()
    if cleaned.startswith("PL"):
        cleaned = cleaned[2:]
    digits = _digits(cleaned, 10)
    if digits is None:
        return False
    checksum = _weighted_mod_11(digits[:9], _NIP_WEIGHTS)
    return checksum != 10 and checksum == digits[9]


def is_valid_regon(value: str) -> bool:
    """Nine- or fourteen-digit REGON, weighted mod 11 with a remainder of 10 folded to 0.

    A 14-digit REGON additionally embeds a valid 9-digit one; both check digits must hold, which
    is why the composite form is verified rather than merely measured for length.
    """
    cleaned = strip_separators(value)
    if (digits := _digits(cleaned, 9)) is not None:
        return _weighted_mod_11(digits[:8], _REGON_9_WEIGHTS) % 10 == digits[8]
    if (digits := _digits(cleaned, 14)) is not None:
        if _weighted_mod_11(digits[:8], _REGON_9_WEIGHTS) % 10 != digits[8]:
            return False
        return _weighted_mod_11(digits[:13], _REGON_14_WEIGHTS) % 10 == digits[13]
    return False


def is_valid_iban(value: str, *, country: str | None = None) -> bool:
    """ISO 13616 mod-97-10. Pass ``country="PL"`` to additionally pin the country and length.

    Polish bank accounts are printed both as a 26-digit NRB and as a 28-character IBAN; only the
    latter carries the country prefix this check needs, so a bare NRB returns ``False`` unless it
    is given its ``PL`` prefix first.
    """
    cleaned = strip_separators(value).upper()
    #: Normalised once, then used for both checks. Comparing the prefix case-insensitively while
    #: pinning the length against a literal `"PL"` meant `country="pl"` silently skipped the length
    #: check — a total function quietly answering a weaker question than the caller asked.
    expected = country.upper() if country is not None else None
    if len(cleaned) < 5 or not _IBAN_BODY.issuperset(cleaned):
        return False
    if not _ASCII_UPPER.issuperset(cleaned[:2]):
        return False
    if not _DIGITS.issuperset(cleaned[2:4]):
        return False
    if expected is not None and cleaned[:2] != expected:
        return False
    if expected == "PL" and len(cleaned) != 28:
        return False
    rearranged = cleaned[4:] + cleaned[:4]
    numeric = "".join(
        str(ord(ch) - ord("A") + 10) if ch.isalpha() else ch for ch in rearranged
    )
    return int(numeric) % 97 == 1
