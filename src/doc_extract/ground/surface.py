"""What a value could have looked like on the page.

Extraction normalises: an amount arrives as `1336.72`, a NIP as `2313460832`, a date as
`2026-06-08`.
The page prints `1 336,72`, `231-346-08-32`, and — depending on where on the page you look —
`2026-06-08` or `08.06.2026`. Grounding a value therefore means deciding whether *some* lawful
rendering of it appears in the source text, which is what this module produces.

**These are properties of Polish invoices, not of this project's renderer.** A comma decimal
separator, a space or non-breaking space grouping thousands, a NIP written in `000-000-00-00`
groups, an IBAN in fours: all of them are conventions a reader of any Polish invoice meets. That
distinction is the whole licence for this module to exist. `eval/pattern.py` is allowed to know the
literal labels `synth/render.py` prints — `Numer faktury:`, `Do zapłaty:` — because its job is to be
the strongest thing that is not a model. **Grounding is not allowed to know them**, and does not
need to: it matches values, never labels, and `tests/test_ground.py` asserts this package
imports nothing from `synth`.

The forms are deliberately generous. A candidate that never occurs costs a failed comparison; a
lawful form left out would report a correctly-read field as ungrounded, and the whole point of the
grounding signal is that an ungrounded value is suspicious.
"""

from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal

from doc_extract.eval.fields import BY_NAME, Match

_CENT = Decimal("0.01")

#: Everything Polish typography uses to group thousands, plus the ASCII space. Built from code
#: points rather than literals: three of the four are invisible in an editor, and a reader of
#: this line has to be able to tell which characters it actually covers.
GROUPING = "".join(map(chr, (0x20, 0x00A0, 0x202F, 0x2009)))

_NON_ALPHANUMERIC = re.compile(r"[^0-9A-Za-z]+")
_WHITESPACE = re.compile(r"\s+")


def candidates(field: str, value: object) -> tuple[str, ...]:
    """Every rendering of `value` this module is prepared to recognise, for `field`'s match class.

    Ordered longest first, so a caller scanning text finds the most specific form rather than a
    prefix of it — `1 336,72` before `1336.72` before `336,72` could never be produced here, but the
    ordering also makes the search deterministic, which matters because a span is reported.
    """
    forms = _forms(BY_NAME[field].match, value)
    return tuple(sorted({form for form in forms if form}, key=lambda form: (-len(form), form)))


def _forms(match: Match, value: object) -> tuple[str, ...]:
    match match:
        case Match.AMOUNT:
            return _amount(value) if isinstance(value, Decimal) else (str(value),)
        case Match.IDENTIFIER:
            return (str(value),)
        case Match.TEXT:
            return (str(value),)
        case Match.EXACT:
            return _date(value) if isinstance(value, dt.date) else _code(str(value))


def _amount(value: Decimal) -> tuple[str, ...]:
    """A money figure, with and without a decimal comma, a thousands break and trailing zeros.

    Both `43.12` and `43,12` are produced, and both `1336,72` and `1 336,72`. The generator prints
    one of them; a real invoice prints whichever its issuer's software chose, and this module is
    read by M7's held-out set as well as by this corpus.
    """
    plain = format(value, "f")
    #: Both directions. The gold may hold `137.3` where the page printed `137,30`, and a model
    #: may answer `137.30` where the gold holds `137.3`; a grounding that knew only one of the
    #: two would report a correctly-read price as ungrounded on 102 documents. Measured.
    exponent = -value.as_tuple().exponent
    grosze = isinstance(exponent, int) and exponent <= 2
    padded = format(value.quantize(_CENT), "f") if grosze else plain
    out: list[str] = []
    for text in {plain, padded, _strip_trailing_zeros(plain)}:
        out.extend(_separator_variants(text))
    return tuple(out)


def _separator_variants(text: str) -> tuple[str, ...]:
    negative, digits = text.startswith("-"), text.lstrip("-")
    whole, _, fraction = digits.partition(".")
    sign = "-" if negative else ""
    grouped = _group(whole)
    bodies = {f"{whole}.{fraction}", f"{whole},{fraction}"} if fraction else {whole}
    if grouped != whole:
        bodies |= {f"{grouped},{fraction}", f"{grouped}.{fraction}"} if fraction else {grouped}
    return tuple(f"{sign}{body}" for body in bodies)


def _group(whole: str) -> str:
    """`1336` to `1 336`. A plain space only: the caller normalises the page's own break."""
    if len(whole) <= 3:
        return whole
    head, tail = whole[:-3], whole[-3:]
    return f"{_group(head)} {tail}"


def _strip_trailing_zeros(text: str) -> str:
    """`137.30` to `137.3`, but never `100` to `1`. The inverse of what a model tends to write."""
    if "." not in text:
        return text
    stripped = text.rstrip("0").rstrip(".")
    return stripped or "0"


def _date(value: dt.date) -> tuple[str, ...]:
    """ISO, and the two dotted forms Polish documents use. Zero-padded and not."""
    return (
        value.isoformat(),
        f"{value.day:02d}.{value.month:02d}.{value.year}",
        f"{value.day}.{value.month}.{value.year}",
        f"{value.day:02d}-{value.month:02d}-{value.year}",
    )


def _code(text: str) -> tuple[str, ...]:
    """A closed-domain code. Rate codes also appear with a percent sign, and with a space."""
    return (text, f"{text}%", f"{text} %")


# --------------------------------------------------------------------------- normalisation


def amount_form(text: str) -> str:
    """A figure in the one shape both sides of a comparison are put into.

    Every grouping character becomes a **plain space** and the decimal comma becomes a point. The
    space is kept rather than deleted so that `netto 1 412,52` keeps the boundary between the word
    and the figure; deleting it glues them into `netto1412.52`, where nothing can tell where the
    number starts. The page and the candidate go through this same function, which is the point —
    normalising them differently is the bug this replaced.
    """
    return "".join(amount_char(character) for character in text)


def amount_char(character: str) -> str:
    if character in GROUPING:
        return " "
    return "." if character == "," else character


def normalise_identifier(text: str) -> str:
    """The same rule `eval/fields.py` scores identifiers by: alphanumerics only, uppercased.

    Deliberately the same, and deliberately a separate implementation from the scorer's. A NIP that
    grounds must be a NIP that would score equal, or the two layers would disagree about what the
    page says — and importing the scorer's private helper would tie a runtime signal to a metric.
    """
    return _NON_ALPHANUMERIC.sub("", text).upper()


def collapse(text: str) -> str:
    """Runs of whitespace to one space. A name that wrapped is the same name."""
    return _WHITESPACE.sub(" ", text).strip()


def tokens(text: str) -> tuple[str, ...]:
    """A text value split into the pieces the page would have drawn as separate words.

    Grounding a description cannot ask for one contiguous span: the renderer wraps a long
    description above and below the row's numbers, so `Wynajem powierzchni magazynowej` is on the
    page as two fragments with an entire table row of text between them.

    Splitting it is all this function does. **Which question is then asked of the pieces belongs to
    `place.py`**, and the answer changed: they were once looked for anywhere on the page, one word
    at a time, and are now required to sit together in one place. The distinction is not pedantic —
    the old reading let a buyer's name ground on the seller's legal form — and it is why the
    fragments above are reunited by *geometry*, the same column a row down, rather than by their
    distance apart in the text.
    """
    return tuple(token for token in collapse(text).split(" ") if token)
