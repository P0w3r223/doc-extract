"""Fixtures: one arithmetically coherent invoice, and helpers to break it one way at a time.

The identifiers below were computed independently of `checksums.py` (a fixture verified by the
code under test would prove nothing) and the amounts reconcile exactly:

    rate 23 %:  lines 200.00 + 50.00 = 250.00 net, 46.00 + 11.50 = 57.50 VAT
    rate  8 %:  line   30.00          =  30.00 net,               2.40 VAT
    P_15     :  250.00 + 57.50 + 30.00 + 2.40 = 339.90
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from pathlib import Path

import pytest

from doc_extract.schema.ksef import Invoice, LineItem, Party, RateTotal

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = REPO_ROOT / "schemas"

#: The FA(3) structure imports the Ministry's shared type definitions, which in turn include two
#: more files, all by absolute `crd.gov.pl` URL. All four are vendored, and this map redirects the
#: URLs at the local copies so validation never reaches the network — see `schemas/PROVENANCE.md`.
_ED_BASE = "http://crd.gov.pl/xml/schematy/dziedzinowe/mf/2022/01/05/eD/DefinicjeTypy/"
_VENDORED = (
    "StrukturyDanych_v10-0E.xsd",
    "ElementarneTypyDanych_v10-0E.xsd",
    "KodyKrajow_v10-0E.xsd",
)


@pytest.fixture(scope="session")
def fa3_schema():
    """The real FA(3) schema, compiled offline.

    `allow="local"` is the assertion that matters as much as the validation itself: it makes any
    attempt to fetch a remote schema an error, so a green test can never mean "the Ministry's
    server happened to be up".
    """
    xmlschema = pytest.importorskip("xmlschema")
    mapper = {_ED_BASE + name: (SCHEMA_DIR / name).as_uri() for name in _VENDORED}
    return xmlschema.XMLSchema(str(SCHEMA_DIR / "fa3.xsd"), uri_mapper=mapper, allow="local")

#: Valid check digits, computed by hand in a throwaway script, not by `checksums.py`.
SELLER_NIP = "1130220189"
BUYER_NIP = "5221234561"
VALID_IBAN = "PL61109010140000071219812874"


def d(value: str) -> Decimal:
    return Decimal(value)


@pytest.fixture
def invoice() -> Invoice:
    """A coherent VAT invoice: every invariant holds."""
    return Invoice(
        kind="VAT",
        number="FV/2026/08/0001",
        issue_date=dt.date(2026, 8, 10),
        sale_date=dt.date(2026, 8, 5),
        currency="PLN",
        seller=Party(name="Acme sp. z o.o.", nip=SELLER_NIP),
        buyer=Party(name="Klient S.A.", nip=BUYER_NIP),
        lines=(
            LineItem(line_no=1, description="Usługa A", quantity=d("2"),
                     unit_price_net=d("100.00"), net=d("200.00"), vat=d("46.00"), vat_rate="23"),
            LineItem(line_no=2, description="Usługa B", quantity=d("1"),
                     unit_price_net=d("50.00"), net=d("50.00"), vat=d("11.50"), vat_rate="23"),
            LineItem(line_no=3, description="Książka", quantity=d("3"),
                     unit_price_net=d("10.00"), net=d("30.00"), vat=d("2.40"), vat_rate="8"),
        ),
        rate_totals=(
            RateTotal(rate="23", net=d("250.00"), vat=d("57.50")),
            RateTotal(rate="8", net=d("30.00"), vat=d("2.40")),
        ),
        total_gross=d("339.90"),
        payment_account=VALID_IBAN,
    )


def totals_only(*, net: str, vat: str, gross: str, rate: str = "23", **over) -> Invoice:
    """An invoice with no line items — isolates the rules that read only the rate totals."""
    return Invoice(
        kind=over.pop("kind", "VAT"),
        number="FV/2026/08/0002",
        issue_date=dt.date(2026, 8, 10),
        currency="PLN",
        seller=Party(name="Acme sp. z o.o.", nip=SELLER_NIP),
        buyer=Party(name="Klient S.A."),
        rate_totals=(RateTotal(rate=rate, net=d(net), vat=d(vat)),),
        total_gross=d(gross),
        **over,
    )
