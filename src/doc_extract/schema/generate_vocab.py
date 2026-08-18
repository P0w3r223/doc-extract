"""Regenerate `vocab.py` from the vendored XSD.

    python -m doc_extract.schema.generate_vocab            # rewrite vocab.py
    python -m doc_extract.schema.generate_vocab --check    # fail if it is out of date

`vocab.py` claims to mirror a national standard, and `tests/test_vocab.py` already fails if its
*values* drift from the schema. This module closes the other half: it makes regeneration a command
rather than a remembered manual edit, so re-vendoring the XSD produces a diff a reviewer can read
instead of a hand transcription nobody can check.

The prose in the generated file is part of the template on purpose. A generated module whose
docstrings had to be re-added by hand after every run would lose them on the first hurried
re-vendor.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

XS = "{http://www.w3.org/2001/XMLSchema}"

#: Rate codes that levy no tax. This one classification is *not* derivable from the XSD: the schema
#: enumerates the markers but says nothing about which of them carry a rate, so the split is ours
#: and has to be kept in step with the standard by hand. `classify_rates` below refuses to write a
#: file it cannot classify, which is what makes that manual step visible instead of optional.
UNTAXED_CODES: tuple[str, ...] = ("0 KR", "0 WDT", "0 EX", "zw", "oo", "np I", "np II")

_ROOT = Path(__file__).resolve().parents[3]
XSD_PATH = _ROOT / "schemas" / "fa3.xsd"
VOCAB_PATH = _ROOT / "src" / "doc_extract" / "schema" / "vocab.py"

#: The source the generated header points at. Kept beside the path so the two are updated together.
SOURCE_URL = "http://crd.gov.pl/wzor/2025/06/25/13775/schemat.xsd"
RETRIEVED = "2026-08-18"

_TEMPLATE = '''"""Closed domains of the KSeF FA(3) structure, transcribed from the vendored XSD.

Every set here is a *closed* domain in the national standard: a value outside it is not a rare
case, it is invalid. Extraction therefore has somewhere to fail loudly rather than inventing a
plausible-looking category — the same discipline `car-price-ml` applies to its vehicle makes.

These constants are generated from `schemas/fa3.xsd` and re-derived from it by
`tests/test_vocab.py`, which fails if the two ever disagree. Do not hand-edit: if the Ministry
republishes the schema, re-vendor the XSD and regenerate, so the drift is a red test and not a
silent divergence between this file and the standard it claims to mirror.

Source: {source} (kodSystemowy "{system_code}", wersjaSchemy
"{schema_version}"), retrieved {retrieved}.
"""

from __future__ import annotations

from decimal import Decimal

#: ISO 4217 codes accepted by the schema ({currency_count} entries, `TKodWaluty`).
CURRENCIES: frozenset[str] = frozenset({{
{currencies}
}})

#: `TRodzajFaktury` — what kind of document this is.
INVOICE_KINDS: frozenset[str] = frozenset({{
{kinds}
}})

#: Kinds that correct an earlier invoice; their amounts may legitimately be negative.
CORRECTION_KINDS: frozenset[str] = frozenset({{"KOR", "KOR_ZAL", "KOR_ROZ"}})

#: `TStawkaPodatku` — the VAT rate marker carried by a line item (`P_12`).
VAT_RATE_CODES: frozenset[str] = frozenset({{
{rates}
}})

#: Rate codes that levy no VAT: zero-rated, exempt, reverse charge, and out-of-scope.
#: They differ in law and in reporting, but all expect a VAT amount of zero.
UNTAXED_RATE_CODES: frozenset[str] = frozenset({{
{untaxed}
}})

#: Rate code -> the fraction to apply to a net amount. `Decimal`, never float: these values are
#: multiplied by money and compared to a value the standard stores at two decimal places.
RATE_FRACTION: dict[str, Decimal] = {{
    **{{code: Decimal(code) / Decimal(100) for code in VAT_RATE_CODES - UNTAXED_RATE_CODES}},
    **{{code: Decimal(0) for code in UNTAXED_RATE_CODES}},
}}
'''


def enumeration(schema: ET.Element, type_name: str) -> list[str]:
    """The values of a closed simple type, in the order the schema declares them."""
    for node in schema.iter(f"{XS}simpleType"):
        if node.get("name") == type_name:
            return [element.get("value") for element in node.iter(f"{XS}enumeration")]
    raise SystemExit(f"simpleType {type_name!r} not found in {XSD_PATH}")


def fixed_attributes(schema: ET.Element) -> dict[str, str]:
    return {
        attribute.get("name"): attribute.get("fixed")
        for attribute in schema.iter(f"{XS}attribute")
        if attribute.get("fixed")
    }


def classify_rates(codes: list[str]) -> None:
    """Fail unless every rate code is either known-untaxed or a number a fraction can be made of.

    `vocab.RATE_FRACTION` builds itself with `Decimal(code)` over the codes that are not in
    `UNTAXED_RATE_CODES`. A republished schema that added a non-numeric marker — the set already
    holds `np I` and `np II`, so another is unremarkable — would therefore be written out happily
    and then raise `decimal.InvalidOperation` on `import vocab`, taking every module in the package
    down with an error naming neither the schema nor the new code.

    Failing here instead puts the error at the one moment a human is already reading a diff.
    """
    unclassified = []
    for code in codes:
        if code in UNTAXED_CODES:
            continue
        try:
            Decimal(code)
        except InvalidOperation:
            unclassified.append(code)
    if unclassified:
        raise SystemExit(
            f"TStawkaPodatku in {XSD_PATH.name} carries {unclassified} — neither a numeric rate "
            f"nor a known untaxed marker. Add each to UNTAXED_CODES in {Path(__file__).name} if it "
            "levies no tax, and regenerate; vocab.RATE_FRACTION cannot be built until you do."
        )

    missing = [code for code in UNTAXED_CODES if code not in codes]
    if missing:
        raise SystemExit(
            f"UNTAXED_CODES lists {missing}, which {XSD_PATH.name} no longer enumerates. Drop them "
            "so the untaxed set stays a subset of the standard rather than outliving it."
        )


def render(schema: ET.Element) -> str:
    """The text of `vocab.py` for this schema."""
    fixed = fixed_attributes(schema)
    currencies = sorted(enumeration(schema, "TKodWaluty"))
    rates = enumeration(schema, "TStawkaPodatku")
    classify_rates(rates)
    return _TEMPLATE.format(
        source=SOURCE_URL,
        system_code=fixed.get("kodSystemowy", "?"),
        schema_version=fixed.get("wersjaSchemy", "?"),
        retrieved=RETRIEVED,
        currency_count=len(currencies),
        currencies=_wrap(currencies, per_line=13),
        kinds=_wrap(enumeration(schema, "TRodzajFaktury"), per_line=7),
        rates=_wrap(rates, per_line=14),
        untaxed=_wrap(list(UNTAXED_CODES), per_line=7),
    )


def _wrap(values: list[str], *, per_line: int) -> str:
    """Fixed-width rows, so a republished schema produces a diff of the lines that changed."""
    rows = [values[start:start + per_line] for start in range(0, len(values), per_line)]
    return "\n".join("    " + " ".join(f'"{value}",' for value in row) for row in rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="doc_extract.schema.generate_vocab", description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if vocab.py differs from the schema, and write nothing")
    args = parser.parse_args(argv)

    generated = render(ET.parse(XSD_PATH).getroot())
    current = VOCAB_PATH.read_text(encoding="utf-8") if VOCAB_PATH.exists() else None

    if generated == current:
        print(f"{VOCAB_PATH.name} is up to date with {XSD_PATH.name}")
        return 0
    if args.check:
        print(f"{VOCAB_PATH.name} is out of date; run without --check to regenerate",
              file=sys.stderr)
        return 1

    VOCAB_PATH.write_text(generated, encoding="utf-8")
    print(f"wrote {VOCAB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
