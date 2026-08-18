"""The material a generated invoice is made of: parties, goods, and valid Polish identifiers.

Everything here is invented. The names are plausible-but-fictional companies and the identifiers
are constructed to satisfy their check digits rather than copied from a register, so no real
taxpayer appears in the corpus. That is a requirement, not a courtesy — the alternative would put
real NIP numbers in a public repository.

**Identifiers are generated here and validated by `schema.checksums`.** The dependency runs one
way on purpose: a check-digit routine that also produced the values it checks would agree with
itself no matter what either half did. `tests/test_synth_pools.py` closes the loop by asserting
that every generated identifier passes the independently written validator.

Every catalogue entry carries the VAT rate its goods actually attract in Polish law — books at 5 %,
construction work at 8 %, training exempt — so a mixed-rate document is mixed for a reason a
reviewer can check, rather than by shuffling rate codes onto arbitrary products.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal

_NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)

#: Real Polish bank prefixes are eight digits; these are drawn from ranges no bank uses, so an
#: account number cannot be mistaken for a routable one while still passing the mod-97 check.
_BANK_PREFIXES = ("99101099", "99102055", "99103011", "99105077", "99114020", "99116022")


@dataclass(frozen=True, slots=True)
class Company:
    name: str
    street: str
    postcode: str
    city: str

    @property
    def address_line(self) -> str:
        return f"{self.street}, {self.postcode} {self.city}"


@dataclass(frozen=True, slots=True)
class Item:
    """One catalogue entry: what is sold, in what unit, at the rate the law puts it on."""

    description: str
    unit: str
    vat_rate: str
    min_price: Decimal
    max_price: Decimal


SELLERS: tuple[Company, ...] = (
    Company("Bartnicki i Wspólnicy sp. z o.o.", "ul. Legnicka 118", "54-206", "Wrocław"),
    Company("Zakład Usług Technicznych OSTOJA S.A.", "al. Jerozolimskie 214", "02-486", "Warszawa"),
    Company("Drukarnia Wielkopolska sp.j.", "ul. Dąbrowskiego 79", "60-529", "Poznań"),
    Company("MERITUM Doradztwo Podatkowe sp. z o.o.", "ul. Świętojańska 44", "81-393", "Gdynia"),
    Company("Przedsiębiorstwo Budowlane KAMBUD sp. z o.o.", "ul. Nowohucka 12", "31-580", "Kraków"),
    Company("Hurtownia Spożywcza ŻÓŁTY DOM sp. z o.o.", "ul. Krakowska 61", "40-050", "Katowice"),
    Company("Studio Graficzne PIKSEL Anna Wróbel", "ul. Piotrkowska 155", "90-440", "Łódź"),
    Company("Transport i Spedycja WIŚLANKA sp. z o.o.", "ul. Portowa 8", "70-832", "Szczecin"),
    Company("Serwis Maszyn Rolniczych AGROMET sp.k.", "ul. Polna 3", "20-095", "Lublin"),
    Company("Wydawnictwo Akademickie LOGOS sp. z o.o.", "ul. Uniwersytecka 22",
            "87-100", "Toruń"),
)

BUYERS: tuple[Company, ...] = (
    Company("Nowak Instalacje sp. z o.o.", "ul. Grunwaldzka 302", "80-314", "Gdańsk"),
    Company("Fundacja Rozwoju Regionalnego HORYZONT", "ul. Kościuszki 15", "35-030", "Rzeszów"),
    Company("EUROTECH Systemy Pomiarowe S.A.", "ul. Przemysłowa 41", "43-100", "Tychy"),
    Company("Gabinet Stomatologiczny Dentimed sp. z o.o.", "ul. Wojska Polskiego 9",
            "10-229", "Olsztyn"),
    Company("Restauracja POD ZEGAREM Marek Sikora", "Rynek 4", "50-106", "Wrocław"),
    Company("Spółdzielnia Mieszkaniowa PODGÓRZE", "ul. Limanowskiego 27", "30-534", "Kraków"),
    Company("BIURO PLUS Obsługa Firm sp. z o.o.", "ul. Sienkiewicza 82", "25-501", "Kielce"),
    Company("Zespół Szkół Technicznych nr 3", "ul. Szkolna 6", "15-640", "Białystok"),
    Company("LOGISTIKA Magazyny i Spedycja sp. z o.o.", "ul. Składowa 55", "61-897", "Poznań"),
    Company("Przychodnia Rodzinna VITAMED sp. z o.o.", "ul. Zielona 18", "45-365", "Opole"),
)

def _item(description: str, unit: str, rate: str, low: int, high: int) -> Item:
    """Price bounds are whole złoty; the fractional part is drawn per document, not catalogued."""
    return Item(description, unit, rate, Decimal(low), Decimal(high))


#: Goods and services, each on the rate Polish VAT actually assigns it.
CATALOGUE: tuple[Item, ...] = (
    _item("Usługa projektowa – opracowanie dokumentacji", "godz.", "23", 120, 340),
    _item("Hosting serwera dedykowanego – abonament miesięczny", "mies.", "23", 199, 890),
    _item("Papier ksero A4 80 g/m², ryza 500 ark.", "op.", "23", 18, 34),
    _item("Toner do drukarki laserowej, zamiennik", "szt.", "23", 89, 310),
    _item("Naprawa i konserwacja maszyny pakującej", "usł.", "23", 450, 2_400),
    _item("Kabel zasilający 3×2,5 mm², bęben 100 m", "m", "23", 4, 11),
    _item("Audyt bezpieczeństwa sieci teleinformatycznej", "usł.", "23", 2_800, 9_500),
    _item("Wynajem powierzchni magazynowej", "m2", "23", 22, 48),
    _item("Szkolenie stanowiskowe BHP – grupa 12 osób", "usł.", "23", 900, 2_100),
    _item("Materiały eksploatacyjne do wózka widłowego", "kpl.", "23", 240, 760),
    _item("Roboty malarskie – klatka schodowa", "m2", "8", 26, 62),
    _item("Wymiana instalacji wodno-kanalizacyjnej w lokalu", "usł.", "8", 1_800, 7_400),
    _item("Usługa hotelowa – nocleg ze śniadaniem", "dob.", "8", 180, 470),
    _item("Przewóz osób – transport autokarowy", "km", "8", 6, 14),
    _item("Roboty dekarskie – wymiana pokrycia", "m2", "8", 95, 240),
    _item("Książka „Rachunkowość zarządcza w praktyce”", "szt.", "5", 59, 129),
    _item("Czasopismo branżowe – prenumerata roczna", "kpl.", "5", 180, 420),
    _item("Pieczywo mieszane, dostawa dzienna", "kg", "5", 6, 18),
    _item("Warzywa świeże – marchew, worek 10 kg", "worek", "5", 14, 39),
    _item("Usługa szkoleniowa ze środków publicznych", "usł.", "zw", 1_400, 5_600),
    _item("Świadczenie opieki medycznej – profilaktyka", "os.", "zw", 90, 260),
    _item("Pośrednictwo w udzielaniu kredytu obrotowego", "usł.", "zw", 2_000, 8_000),
    _item("Roboty budowlane – podwykonawstwo, konstrukcja", "usł.", "oo", 4_200, 18_000),
    _item("Dostawa złomu stalowego posortowanego", "t", "oo", 780, 1_450),
    _item("Dostawa wewnątrzwspólnotowa – podzespoły", "szt.", "0 WDT", 140, 620),
    _item("Eksport towarów – armatura przemysłowa", "szt.", "0 EX", 310, 1_290),
)

BANKS: tuple[str, ...] = (
    "Bank Spółdzielczy w Oławie",
    "Powszechny Bank Regionalny S.A.",
    "Bank Gospodarki Lokalnej S.A.",
    "Nadwiślański Bank Handlowy S.A.",
)

#: `TFormaPlatnosci` codes: 1 gotówka, 2 karta, 3 bon, 4 czek, 5 kredyt, 6 przelew, 7 mobilna.
PAYMENT_FORMS: tuple[tuple[str, str], ...] = (
    ("6", "Przelew"),
    ("1", "Gotówka"),
    ("2", "Karta płatnicza"),
    ("7", "Płatność mobilna"),
)

CORRECTION_REASONS: tuple[str, ...] = (
    "Zwrot części towaru przez nabywcę",
    "Udzielenie rabatu potransakcyjnego",
    "Pomyłka w ilości wykazanej na fakturze pierwotnej",
    "Reklamacja uznana – obniżenie ceny",
)

ISSUE_PLACES: tuple[str, ...] = ("Wrocław", "Warszawa", "Poznań", "Kraków", "Gdańsk", "Katowice")


def nip(rng: random.Random) -> str:
    """A ten-digit NIP whose check digit holds and whose shape matches `etd:TNrNIP`.

    The pattern in the schema forbids a leading zero and forbids the second and third digits both
    being zero; a weighted remainder of 10 belongs to no valid NIP, so those draws are discarded.
    """
    while True:
        digits = [rng.randint(1, 9)] + [rng.randint(0, 9) for _ in range(8)]
        if digits[1] == 0 and digits[2] == 0:
            continue
        checksum = sum(d * w for d, w in zip(digits, _NIP_WEIGHTS, strict=True)) % 11
        if checksum == 10:
            continue
        return "".join(str(d) for d in [*digits, checksum])


def iban(rng: random.Random) -> str:
    """A Polish IBAN: `PL`, two check digits, then 24 digits — 28 characters in all.

    The Polish NRB is 26 digits, the first two of which *are* those check digits; the remaining 24
    are an eight-digit bank and branch code followed by a sixteen-digit account. Getting that split
    wrong is the classic way to produce a plausible-looking account that fails mod-97, which is
    exactly why `tests/test_synth_pools.py` runs every generated value through `checksums`.
    """
    bban = rng.choice(_BANK_PREFIXES) + "".join(str(rng.randint(0, 9)) for _ in range(16))
    rearranged = bban + "252100"          # "PL00" as digits: P=25, L=21, then the two zero checks
    check = 98 - int(rearranged) % 97
    return f"PL{check:02d}{bban}"


def format_iban(value: str) -> str:
    """`PL61 1090 1014 …` — how an account is printed, as against how it is stored."""
    return f"{value[:2]} {value[2:4]} " + " ".join(
        value[i:i + 4] for i in range(4, len(value), 4)
    )


def format_nip(value: str) -> str:
    """`113-022-01-89` — the dashed form that appears on roughly half of real invoices."""
    return f"{value[:3]}-{value[3:6]}-{value[6:8]}-{value[8:]}"
