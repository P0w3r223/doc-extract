"""Closed domains of the KSeF FA(3) structure, transcribed from the vendored XSD.

Every set here is a *closed* domain in the national standard: a value outside it is not a rare
case, it is invalid. Extraction therefore has somewhere to fail loudly rather than inventing a
plausible-looking category — the same discipline `car-price-ml` applies to its vehicle makes.

These constants are generated from `schemas/fa3.xsd` and re-derived from it by
`tests/test_vocab.py`, which fails if the two ever disagree. Do not hand-edit: if the Ministry
republishes the schema, re-vendor the XSD and regenerate, so the drift is a red test and not a
silent divergence between this file and the standard it claims to mirror.

Source: http://crd.gov.pl/wzor/2025/06/25/13775/schemat.xsd (kodSystemowy "FA (3)", wersjaSchemy
"1-0E"), retrieved 2026-08-18.
"""

from __future__ import annotations

from decimal import Decimal

#: ISO 4217 codes accepted by the schema (182 entries, `TKodWaluty`).
CURRENCIES: frozenset[str] = frozenset({
    "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN", "BAM", "BBD", "BDT",
    "BGN", "BHD", "BIF", "BMD", "BND", "BOB", "BOV", "BRL", "BSD", "BTN", "BWP", "BYN", "BZD",
    "CAD", "CDF", "CHE", "CHF", "CHW", "CLF", "CLP", "CNY", "COP", "COU", "CRC", "CUC", "CUP",
    "CVE", "CZK", "DJF", "DKK", "DOP", "DZD", "EGP", "ERN", "ETB", "EUR", "FJD", "FKP", "GBP",
    "GEL", "GGP", "GHS", "GIP", "GMD", "GNF", "GTQ", "GYD", "HKD", "HNL", "HRK", "HTG", "HUF",
    "IDR", "ILS", "IMP", "INR", "IQD", "IRR", "ISK", "JEP", "JMD", "JOD", "JPY", "KES", "KGS",
    "KHR", "KMF", "KPW", "KRW", "KWD", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD", "LSL", "LYD",
    "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRU", "MUR", "MVR", "MWK", "MXN", "MXV",
    "MYR", "MZN", "NAD", "NGN", "NIO", "NOK", "NPR", "NZD", "OMR", "PAB", "PEN", "PGK", "PHP",
    "PKR", "PLN", "PYG", "QAR", "RON", "RSD", "RUB", "RWF", "SAR", "SBD", "SCR", "SDG", "SEK",
    "SGD", "SHP", "SLL", "SOS", "SRD", "SSP", "STN", "SVC", "SYP", "SZL", "THB", "TJS", "TMT",
    "TND", "TOP", "TRY", "TTD", "TWD", "TZS", "UAH", "UGX", "USD", "USN", "UYI", "UYU", "UYW",
    "UZS", "VES", "VND", "VUV", "WST", "XAF", "XAG", "XAU", "XBA", "XBB", "XBC", "XBD", "XCD",
    "XCG", "XDR", "XOF", "XPD", "XPF", "XPT", "XSU", "XUA", "XXX", "YER", "ZAR", "ZMW", "ZWL",
})

#: `TRodzajFaktury` — what kind of document this is.
INVOICE_KINDS: frozenset[str] = frozenset({
    "VAT", "KOR", "ZAL", "ROZ", "UPR", "KOR_ZAL", "KOR_ROZ",
})

#: Kinds that correct an earlier invoice; their amounts may legitimately be negative.
CORRECTION_KINDS: frozenset[str] = frozenset({"KOR", "KOR_ZAL", "KOR_ROZ"})

#: `TStawkaPodatku` — the VAT rate marker carried by a line item (`P_12`).
VAT_RATE_CODES: frozenset[str] = frozenset({
    "23", "22", "8", "7", "5", "4", "3", "0 KR", "0 WDT", "0 EX", "zw", "oo", "np I", "np II",
})

#: Rate codes that levy no VAT: zero-rated, exempt, reverse charge, and out-of-scope.
#: They differ in law and in reporting, but all expect a VAT amount of zero.
UNTAXED_RATE_CODES: frozenset[str] = frozenset({
    "0 KR", "0 WDT", "0 EX", "zw", "oo", "np I", "np II",
})

#: Rate code -> the fraction to apply to a net amount. `Decimal`, never float: these values are
#: multiplied by money and compared to a value the standard stores at two decimal places.
RATE_FRACTION: dict[str, Decimal] = {
    **{code: Decimal(code) / Decimal(100) for code in VAT_RATE_CODES - UNTAXED_RATE_CODES},
    **{code: Decimal(0) for code in UNTAXED_RATE_CODES},
}
