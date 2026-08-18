"""Generated identifiers must pass the validators written independently of them.

The dependency runs one way on purpose. `pools` constructs NIP and IBAN check digits; `checksums`
verifies them and knows nothing about how they were made. A single module doing both would agree
with itself whatever either half got wrong — which is exactly how a corpus ends up full of
plausible identifiers that no real system would accept.
"""

from __future__ import annotations

import random
import re

from doc_extract.schema import vocab
from doc_extract.schema.checksums import is_valid_iban, is_valid_nip
from doc_extract.synth import pools

#: `etd:TNrNIP` in the vendored schema: no leading zero, and not both of digits two and three zero.
NIP_PATTERN = re.compile(r"[1-9]((\d[1-9])|([1-9]\d))\d{7}$")


def test_generated_nips_pass_the_check_digit():
    rng = random.Random(0)
    assert all(is_valid_nip(pools.nip(rng)) for _ in range(500))


def test_generated_nips_match_the_schema_pattern():
    """A valid check digit is not enough — the structure also constrains the shape."""
    rng = random.Random(1)
    assert all(NIP_PATTERN.match(pools.nip(rng)) for _ in range(500))


def test_generated_ibans_pass_mod_97():
    rng = random.Random(2)
    assert all(is_valid_iban(pools.iban(rng), country="PL") for _ in range(500))


def test_generated_ibans_are_twenty_eight_characters():
    """`PL`, two check digits, and 24 more. Getting the split wrong is the classic mistake."""
    rng = random.Random(3)
    assert all(len(pools.iban(rng)) == 28 for _ in range(100))


def test_every_catalogue_rate_is_a_code_the_standard_recognises():
    """An invented rate would fail schema validation only once a whole corpus had been built."""
    assert {item.vat_rate for item in pools.CATALOGUE} <= vocab.VAT_RATE_CODES


def test_no_catalogue_rate_is_one_the_writer_refuses():
    """22 % and 7 % share their block with another code and cannot be read back."""
    from doc_extract.synth.rate_slots import AMBIGUOUS

    assert {item.vat_rate for item in pools.CATALOGUE}.isdisjoint(AMBIGUOUS)


def test_every_rate_used_by_a_tier_has_something_to_sell():
    """A tier naming a rate no catalogue entry carries would fail at generation time."""
    from doc_extract.synth.tiers import TIERS

    available = {item.vat_rate for item in pools.CATALOGUE}
    for tier in TIERS:
        assert set(tier.rates) <= available, tier.name


def test_price_ranges_are_ordered_and_positive():
    for item in pools.CATALOGUE:
        assert 0 < item.min_price <= item.max_price


def test_printed_identifier_forms_strip_back_to_the_stored_ones():
    """The page prints separators the gold does not carry; the two must reconcile."""
    from doc_extract.schema.checksums import strip_separators

    rng = random.Random(4)
    for _ in range(50):
        value = pools.nip(rng)
        assert strip_separators(pools.format_nip(value)) == value
        account = pools.iban(rng)
        assert strip_separators(pools.format_iban(account)) == account
