"""Every extracted value, against the page it was supposed to come from.

The arithmetic detector in `eval/detector.py` answers "is something wrong with this document" and,
measured on a real model's mistakes, it catches **every** arithmetic error and **none** of the
textual ones: its misses are descriptions and names, fields with no redundancy behind them for a
sum to check. This module is the complement, and that measurement is why it exists rather than a
guess that it might be useful. A description the model invented resolves to nothing on the page; a
description it read resolves, even when the renderer wrapped it around the row's own numbers.

**Grounding is a runtime signal, not a metric.** It compares a value with the source document, never
with the gold — the same discipline the detector follows, and for the same reason: the signal has to
be available on a document nobody annotated.

**A value is looked for inside the text, not as a whole cell.** The first cut of this module matched
cell texts exactly and failed on 14.9 % of *gold* fields, which is the control that caught it: one
of the three layouts prints a whole row as one prose sentence, so `1 412,52` sits mid-clause; an
account number arrives as `Rachunek: PL 91 9910 … (Bank …)`. In both, the value is a substring of
its cell. So the text is projected through the normalisation its match class needs — grouping made
a plain space and the decimal comma a point, or alphanumerics only and uppercased — and searched as
a substring, every projected character remembering the offset it came from so a hit maps back to
spans on the page. The candidate goes through the *same* function as the page.

**Three levels of support, because two would lie.** A value is `GROUNDED` when everything it claims
is on the page, `UNGROUNDED` when none of it is, and `PARTIAL` in between. The middle level is not
hedging: a wrapped description whose first half was read and whose second half was invented is a
real failure, and collapsing it either way would hide the error this module exists to see.

**Some values are excluded from the question rather than answered badly.** A field the invoice does
not carry is `ABSENT` — a row with no discount and a prediction that says `null` have agreed about
the page. A field whose value the page has no literal form of is `NOT_PRINTED`: `kind` is the FA(3)
code `KOR` while the page says *Faktura korygująca*, and a non-numeric rate is an exemption code
each issuer abbreviates their own way. Both are kept out of every denominator. The rate case shows
why that matters rather than being tidy-mindedness: the usual abbreviation of `oo` is a substring of
`sp. z o.o.`, so a grounding that insisted on an answer would ground the tax rate against the
seller's legal form and call it evidence.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum

from doc_extract.eval import fields
from doc_extract.eval.fields import BY_NAME, Match
from doc_extract.ground import surface
from doc_extract.schema.ksef import Invoice
from doc_extract.source.document import SourceDocument, Span

#: Fields whose value is a code the page never prints. Grounding them is not a question this module
#: can answer, so it declines to: `kind` is `VAT`/`KOR`/`ZAL`/`UPR` in the standard, while the page
#: prints the Polish name of the document. `KOR` does appear inside a correction's own number, which
#: is worse than it not appearing — it would ground for a reason that has nothing to do with the
#: field being right.
NOT_PRINTED: frozenset[str] = frozenset({"kind"})

#: Rate fields carry either a percentage or an exemption code. A percentage is printed as a number
#: and grounds like any other; a code does not, and asking for it is worse than not asking.
_RATE_FIELDS: frozenset[str] = frozenset({"lines[].vat_rate", "rate_totals[].rate"})


def _not_printed(field: str, value: object) -> bool:
    """Whether this value is one the page has no literal form of, so grounding cannot ask about it.

    Two cases, and both are statements about Polish invoices rather than about this project's
    renderer — which is the line this package is not allowed to cross:

    * `kind` is an FA(3) code. The page names the document in Polish.
    * A **non-numeric** rate is an exemption code (`zw`, `oo`, `np`), and every issuer abbreviates
      it their own way. Worse than absent: the usual abbreviation of `oo` collides with `sp. z
      o.o.` in a company name, so a naive match grounds the rate against the seller. A numeric rate
      is printed as a number and is asked about normally.
    """
    if field in NOT_PRINTED:
        return True
    return field in _RATE_FIELDS and not str(value).replace(".", "").isdigit()


class Support(StrEnum):
    """How much of a value was found on the page. Exactly one applies, and they partition."""

    GROUNDED = "grounded"
    PARTIAL = "partial"
    UNGROUNDED = "ungrounded"
    #: The field carries no value, so there is nothing to look for. Not a failure.
    ABSENT = "absent"
    #: The field is a code the page does not print. Not answerable, so not answered.
    NOT_PRINTED = "not_printed"


#: The supports over which a coverage figure exists, and the only ones a rate may count.
MEASURED = frozenset({Support.GROUNDED, Support.PARTIAL, Support.UNGROUNDED})


@dataclass(frozen=True, slots=True)
class Grounding:
    """One field instance, and where on the page it came from — or that it did not."""

    field: str
    key: str
    value: str | None
    support: Support
    #: The fraction of the value's parts found on the page: 1.0 or 0.0 for an atomic value, and the
    #: share of a description's words. `None` when the field was not a question this module asked.
    coverage: float | None
    spans: tuple[Span, ...] = ()

    @property
    def measured(self) -> bool:
        """Whether this instance belongs in a denominator at all."""
        return self.support in MEASURED

    @property
    def suspicious(self) -> bool:
        """Whether a routing layer should hesitate over this value.

        `PARTIAL` counts. A half-grounded description is not a lesser version of a grounded one —
        it is the shape a fabricated continuation takes.
        """
        return self.support in (Support.UNGROUNDED, Support.PARTIAL)


def resolve(document: SourceDocument, invoice: Invoice) -> tuple[Grounding, ...]:
    """Ground every scored field instance of an invoice against one source document.

    Walks `fields.read`, so the instances and their keys are the ones the scorer names. A grounding
    keyed differently from the scorer could not be read beside a score, and reading them together
    is the point.
    """
    page = _Page(document)
    reading = fields.read(invoice)
    return tuple(
        _ground(field.name, key, reading.get(field.name, key), page)
        for field in fields.FIELDS
        for key in _keys(field.name, reading)
    )


def _keys(field: str, reading: fields.Reading) -> tuple[str, ...]:
    return tuple(key for (name, key) in reading.values if name == field)


def _ground(field: str, key: str, value: object | None, page: _Page) -> Grounding:
    if value is None:
        return Grounding(field, key, None, Support.ABSENT, None)
    rendered = fields.render(value)
    if _not_printed(field, value):
        return Grounding(field, key, rendered, Support.NOT_PRINTED, None)

    if BY_NAME[field].match is Match.TEXT:
        #: Tokens that are pure punctuation carry nothing to look for. The renderer draws an en
        #: dash inside a description as its own word, and asking the page for it would dock every
        #: such description a seventh of its coverage for a character no reading could get wrong.
        wanted = tuple(t for t in surface.tokens(str(value)) if _bare(t))
        spans = page.find_words(wanted)
        coverage = len(spans) / len(wanted) if wanted else 1.0
    else:
        spans = page.find_value(surface.candidates(field, value), BY_NAME[field].match)
        coverage = 1.0 if spans else 0.0

    return Grounding(field, key, rendered, _support(coverage), coverage, spans)


def _support(coverage: float) -> Support:
    if coverage >= 1.0:
        return Support.GROUNDED
    return Support.UNGROUNDED if coverage <= 0.0 else Support.PARTIAL


# --------------------------------------------------------------------------- the page, indexed


@dataclass(frozen=True, slots=True)
class _Projection:
    """The document text under one normalisation, with each kept character's original offset."""

    text: str
    origin: tuple[int, ...]


class _Page:
    """One document, projected the ways a lookup needs it. Built once; asked sixty-odd questions."""

    __slots__ = ("_amounts", "_identifiers", "_literal", "_source", "_spans", "_words")

    def __init__(self, document: SourceDocument) -> None:
        self._source = document.text
        self._spans = document.words
        self._amounts = _project(document.text, _as_amount)
        self._identifiers = _project(document.text, _as_identifier)
        #: Built here like the other two: `_Page` exists to be built once and asked sixty
        #: times, and rebuilding the identity map per lookup quietly undid that.
        self._literal = _Projection(document.text, tuple(range(len(document.text))))

        self._words: dict[str, list[Span]] = {}
        for span in document.words:
            _add(self._words, _bare(document.text_of(span)), span)

    def find_value(self, candidates: tuple[str, ...], match: Match) -> tuple[Span, ...]:
        """Spans covering the first candidate that occurs on the page, in candidate order."""
        for candidate in candidates:
            ranges = self._occurrences(candidate, match)
            if ranges:
                return tuple(span for start, end in ranges for span in self._covering(start, end))
        return ()

    def _occurrences(self, candidate: str, match: Match) -> list[tuple[int, int]]:
        if match is Match.AMOUNT:
            return self._scan(self._amounts, surface.amount_form(candidate), _amount_boundary)
        if match is Match.IDENTIFIER:
            return self._scan(
                self._identifiers, surface.normalise_identifier(candidate), self._source_boundary
            )
        return self._scan(self._literal, candidate, self._source_boundary)

    def _scan(
        self,
        projection: _Projection,
        needle: str,
        bounded: Callable[[_Projection, int, int], bool],
    ) -> list[tuple[int, int]]:
        if not needle:
            return []
        found: list[tuple[int, int]] = []
        at = projection.text.find(needle)
        while at != -1:
            end = at + len(needle)
            if bounded(projection, at, end):
                found.append((projection.origin[at], projection.origin[end - 1] + 1))
            at = projection.text.find(needle, at + 1)
        return found

    def _source_boundary(self, projection: _Projection, start: int, end: int) -> bool:
        """A hit must not sit inside a longer run of letters or digits on the *page*.

        Checked against the original text rather than the projection, because the identifier
        projection keeps only alphanumerics and has therefore thrown away every boundary there was.
        """
        before = projection.origin[start] - 1
        after = projection.origin[end - 1] + 1
        return not (
            (before >= 0 and self._source[before].isalnum())
            or (after < len(self._source) and self._source[after].isalnum())
        )

    def _covering(self, start: int, end: int) -> Iterable[Span]:
        return (span for span in self._spans if span.start < end and span.end > start)

    def find_words(self, wanted: tuple[str, ...]) -> tuple[Span, ...]:
        """The spans of those of a text value's words that are on the page, with multiplicity.

        Counted with multiplicity: a description claiming a word twice needs it on the page twice,
        or one of the two is unaccounted for. Without that, a fabricated repetition would ground
        against a single occurrence elsewhere on the invoice.
        """
        remaining: dict[str, list[Span]] = {}
        found: list[Span] = []
        for token in wanted:
            bare = _bare(token)
            available = remaining.setdefault(bare, list(self._words.get(bare, ())))
            if available:
                found.append(available.pop(0))
        return tuple(found)


def _amount_boundary(projection: _Projection, start: int, end: int) -> bool:
    """A figure must not be part of a longer one — but a sentence's comma is not a decimal point.

    Rejecting any adjacent `.` outright was too strong: the page writes `netto 1 412,52, VAT …`, and
    that trailing comma is a projected `.` which would disqualify a perfectly good hit. A decimal
    point is one with a digit on its far side, so that is what the rule asks. Without the rule at
    all, `52` would ground against the fraction of `1412.52` and `1412` against its whole part.
    """
    text = projection.text
    return not (_runs_on(text, start - 1, -1) or _runs_on(text, end, 1))


def _runs_on(text: str, at: int, step: int) -> bool:
    """Whether the character at `at` continues a number rather than ending it."""
    if not 0 <= at < len(text):
        return False
    if text[at].isdigit():
        return True
    beyond = at + step
    return text[at] == "." and 0 <= beyond < len(text) and text[beyond].isdigit()


def _project(text: str, transform: Callable[[str], str | None]) -> _Projection:
    """Text under a per-character transform, keeping the origin of every character that survives."""
    kept: list[str] = []
    origin: list[int] = []
    for offset, character in enumerate(text):
        replacement = transform(character)
        if replacement is not None:
            kept.append(replacement)
            origin.append(offset)
    return _Projection("".join(kept), tuple(origin))


def _as_amount(character: str) -> str | None:
    """The page's characters, in the shape `surface.amount_form` also puts a candidate into."""
    return surface.amount_char(character)


def _as_identifier(character: str) -> str | None:
    return character.upper() if character.isalnum() else None


#: Punctuation a line-join or a sentence puts around a word. The last three are written as code
#: points because an ellipsis and the two dashes are hard to tell apart from a hyphen in a diff, and
#: the difference decides whether a description's dash is stripped or looked for on the page.
_EDGE_PUNCTUATION = ".,;:()[]\"'" + "".join(map(chr, (0x2026, 0x2013, 0x2014)))


def _bare(token: str) -> str:
    """A word without the punctuation a line-join or a sentence put around it.

    The gold joins an address's lines with a comma, so its second token is `4,` while the page drew
    `4`. Stripping the edges makes the two the same word, and keeps `50-106` and `m²` intact, which
    a blanket alphanumeric filter would not.
    """
    return token.strip(_EDGE_PUNCTUATION)


def _add(table: dict[str, list[Span]], key: str, span: Span) -> None:
    if key:
        table.setdefault(key, []).append(span)
