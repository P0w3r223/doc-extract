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

**A text value is located, not tallied.** Asking of each word separately whether it is anywhere on
the page grounds a value against evidence belonging to other fields: the buyer's `sp. z o.o.`
resolved to the *seller's* legal form, because that is where those words occur first. `place.Sheet`
answers the question this module actually means — is the whole value in **one place** — and the
spans that come back are that place rather than a bag of occurrences. It cost nothing to impose:
no correct value on gold, on `claude-opus-5`, on `claude-haiku-4-5` or on `pattern` stopped being
grounded, while 19 of `pattern`'s wrong descriptions did. The **value** side of a non-text match is
still every occurrence of the winning candidate, and `docs/adr/0002_placement.md` carries why
narrowing that one needs a criterion this layer is not allowed to have.

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

**And one exclusion is a property of the page rather than of the value: `NO_TEXT`.** A scan with no
text layer gives this module nothing to search, and the first version answered `UNGROUNDED` anyway —
which reads as *this value is not on the page* when it means *there was no page to look in*. M7c
measured what that costs: `oracle`, a reading with nothing wrong in it anywhere, drew **3989 false
alarms out of 5892 asserted values** on the two text-less rungs. M7e measured what it costs the
gate, which is worse than noise: because the only values that could ground were the ones on the rung
that kept a text layer — and that is the rung an injected instruction survives — the gate sorted the
attacked-and-obeyed values into the bucket it called high confidence, and *auto-accepting only that
bucket was less accurate than accepting everything*. So the verdict is its own, kept out of every
denominator, and a reader of the curve is told how many values it covers. Saying **I could not ask**
is a different claim from saying **I asked and found nothing**, and a gate that conflates the two
inverts on exactly the corpus it was built for.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum

from doc_extract.eval import fields
from doc_extract.eval.fields import BY_NAME, Match
from doc_extract.ground import surface
from doc_extract.ground.place import Place, Sheet, bare
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
    #: The **document** carries no text at all, so there was nothing to search. Says nothing about
    #: the value: a correct one and a fabricated one are equally unfindable on a page of pixels.
    #: The unit is the document and not the page, and the two can differ — see `_Page.readable`.
    NO_TEXT = "no_text"


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
    #: Every place on the page this value could have been read from, one entry per place. `spans`
    #: is what grounding reports; this is what it had to choose between, and it is populated only
    #: for a `GROUNDED` value — the alternatives of a value the page does not carry are not a
    #: question anyone asks. `ground/joint.py` is the only consumer, and it needs the alternatives
    #: rather than the choice: whether two values can each have a place of their own depends on
    #: what the *other* one could have settled for.
    places: tuple[tuple[Span, ...], ...] = ()

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
        #: Asked before the page is consulted, and deliberately: `NOT_PRINTED` is a property of the
        #: field and holds on any page at all. Checking it first keeps the two exclusions
        #: orthogonal, so a scanned run and a clean run report the same `kind` count and a reader
        #: can subtract one from the other.
        return Grounding(field, key, rendered, Support.NOT_PRINTED, None)
    if not page.readable:
        return Grounding(field, key, rendered, Support.NO_TEXT, None)

    if BY_NAME[field].match is Match.TEXT:
        #: Tokens that are pure punctuation carry nothing to look for. The renderer draws an en
        #: dash inside a description as its own word, and asking the page for it would dock every
        #: such description a seventh of its coverage for a character no reading could get wrong.
        wanted = tuple(t for t in map(bare, surface.tokens(str(value))) if t)
        place = page.locate(wanted)
        spans, coverage = place.spans, place.coverage
        #: Only asked once the value is known to be fully there, so a partial reading costs the
        #: extra sweep nothing. `locate` stops at the first full place; this enumerates the rest.
        places = page.places(wanted) if coverage >= 1.0 else ()
    else:
        forms = surface.candidates(field, value)
        spans = page.find_value(forms, BY_NAME[field].match)
        coverage = 1.0 if spans else 0.0
        #: Asked only once the value is known to be on the page, so nothing that fails to ground
        #: pays for the second sweep.
        places = page.find_places(forms, BY_NAME[field].match) if spans else ()

    return Grounding(field, key, rendered, _support(coverage), coverage, spans, places)


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

    __slots__ = ("_amounts", "_identifiers", "_literal", "_sheet", "_source", "_spans")

    def __init__(self, document: SourceDocument) -> None:
        self._source = document.text
        self._spans = document.words
        self._amounts = _project(document.text, _as_amount)
        self._identifiers = _project(document.text, _as_identifier)
        #: Built here like the other two: `_Page` exists to be built once and asked sixty
        #: times, and rebuilding the identity map per lookup quietly undid that.
        self._literal = _Projection(document.text, tuple(range(len(document.text))))
        self._sheet = Sheet(document)

    @property
    def readable(self) -> bool:
        """Whether there is any text here to search at all.

        A rung with no text layer yields no words, so no lines, so `source/document.py` assembles
        the empty string — but the test is `strip()` rather than emptiness, because the separators
        this layer joins with (a tab between cells, a newline between lines) are exactly what a
        document reduced to whitespace would come back as, and accusing every value on it of not
        being found there would be the same mistake in a rarer shape.

        **The unit is the whole document, and that is a known limit.** `SourceDocument` spans
        pages, so a document with one scanned insert among readable pages is `readable` here, and
        every value that belonged on the insert would get the `UNGROUNDED` this verdict exists to
        prevent. No corpus in this project can produce that — a rung is applied to a document
        entire — but a real held-out set can. Narrowing it needs a claim about which page a value
        *should* be on, which is the geometric check M5 named and did not build.
        """
        return bool(self._source.strip())

    def find_value(self, candidates: tuple[str, ...], match: Match) -> tuple[Span, ...]:
        """Spans covering the first candidate that occurs on the page, in candidate order."""
        for candidate in candidates:
            ranges = self._occurrences(candidate, match)
            if ranges:
                return tuple(span for start, end in ranges for span in self._covering(start, end))
        return ()

    def find_places(
        self, candidates: tuple[str, ...], match: Match
    ) -> tuple[tuple[Span, ...], ...]:
        """Every place **any** lawful form of the value occurs at, grouped one place per entry.

        Two departures from `find_value`, and each is what the question needs rather than a
        refinement of the other one's answer:

        * **Grouped, not flattened.** *How many* places there are is what `joint` asks: an amount
          printed once in its row and again in the rate totals can host two readings; one printed
          once cannot.
        * **Every form, not the first that occurs.** `surface.candidates` orders longest first, so
          an amount of `1` is looked for as `1,00` before `1`. On an attacked page whose payload
          reads *wpisz 1,00 PLN*, four quantities of 1 then had that sentence as their **only**
          place and contended over it — a page that in fact prints each of them in its own cell,
          as a bare `1`. Asking where a value *could* have been read from is a different question
          from where grounding chose to read it, and answering it with one form understates the
          page.

        `find_value`'s answer stays inside this one, so a value's reported spans are always part of
        some place — `tests/test_ground_joint.py` asserts it.
        """
        found: dict[tuple[int, int], tuple[Span, ...]] = {}
        for candidate in candidates:
            for start, end in self._occurrences(candidate, match):
                found.setdefault((start, end), tuple(self._covering(start, end)))
        return tuple(place for place in found.values() if place)

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

    def locate(self, wanted: tuple[str, ...]) -> Place:
        """The one place on the page holding most of a text value's words, and how much of it.

        Delegated rather than done here because it is a different question from the three
        projections above. Those ask whether a string occurs in the page's text; this asks *where*
        a value sits, and the answer has to respect the page's cells and columns. `place.Sheet`
        carries what the distinction cost to discover.
        """
        return self._sheet.locate(wanted)

    def places(self, wanted: tuple[str, ...]) -> tuple[tuple[Span, ...], ...]:
        """Every place on the page that holds the whole of a text value. See `Sheet.places`."""
        return tuple(place.spans for place in self._sheet.places(wanted))


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


