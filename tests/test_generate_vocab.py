"""`vocab.py` must be exactly what the generator produces from the vendored XSD.

`test_vocab.py` already checks that the *values* match the schema. This checks the stronger thing:
that the file on disk is byte-for-byte the generator's output. Together they mean a hand-edit is a
red test, and re-vendoring the schema produces a reviewable diff rather than a transcription
somebody has to trust.
"""

from __future__ import annotations

from xml.etree import ElementTree

from doc_extract.schema import generate_vocab


def test_the_committed_vocab_is_what_the_generator_writes():
    generated = generate_vocab.render(ElementTree.parse(generate_vocab.XSD_PATH).getroot())
    assert generated == generate_vocab.VOCAB_PATH.read_text(encoding="utf-8"), (
        "vocab.py has drifted from schemas/fa3.xsd — run "
        "`python -m doc_extract.schema.generate_vocab`"
    )


def test_check_mode_reports_success_and_writes_nothing():
    before = generate_vocab.VOCAB_PATH.read_bytes()
    assert generate_vocab.main(["--check"]) == 0
    assert generate_vocab.VOCAB_PATH.read_bytes() == before


def test_the_generated_header_names_the_schema_version():
    """A generated file that did not say which republication it came from would age silently."""
    generated = generate_vocab.render(ElementTree.parse(generate_vocab.XSD_PATH).getroot())
    assert 'kodSystemowy "FA (3)"' in generated
    assert generate_vocab.SOURCE_URL in generated


def test_a_missing_type_fails_loudly():
    """Silence would mean an empty closed domain, which accepts nothing and explains nothing."""
    import pytest

    empty = ElementTree.fromstring('<schema xmlns="http://www.w3.org/2001/XMLSchema"/>')
    with pytest.raises(SystemExit, match="TKodWaluty"):
        generate_vocab.enumeration(empty, "TKodWaluty")


def test_a_new_rate_code_fails_at_generation_rather_than_at_import():
    """`RATE_FRACTION` does `Decimal(code)`, so an unclassifiable marker is an `ImportError` later.

    The schema already enumerates `np I` and `np II`, so another non-numeric marker in a
    republication is unremarkable. Written out unclassified it would take down every module that
    imports `vocab`, with an error naming neither the schema nor the code. This turns it into a
    message at the moment somebody is already reviewing the re-vendored diff.
    """
    import pytest

    with pytest.raises(SystemExit, match="np III"):
        generate_vocab.classify_rates(["23", "8", "np III", *generate_vocab.UNTAXED_CODES])


def test_an_untaxed_code_the_schema_dropped_fails_too():
    """The classification is ours, so it can outlive the standard in either direction."""
    import pytest

    with pytest.raises(SystemExit, match="no longer enumerates"):
        generate_vocab.classify_rates(["23", "8", "5"])


def test_every_rate_the_schema_carries_is_classifiable_today():
    """The guard is worth nothing if the vendored schema does not actually pass it."""
    schema = ElementTree.parse(generate_vocab.XSD_PATH).getroot()
    generate_vocab.classify_rates(generate_vocab.enumeration(schema, "TStawkaPodatku"))
