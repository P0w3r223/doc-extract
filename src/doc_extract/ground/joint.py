"""One place holds one value — so a reading's values are placed together or not at all.

`resolve` grounds each field on its own: is *this* value on the page. A reading whose every value
answers yes can still be incoherent, because the answers can be the **same ink twice**. M7i is where
that stopped being hypothetical. `claude-haiku-4-5` reading the foreign corpus asserts 58
`lines[].discount` values the gold does not have, and the ADR recorded them as one failure — *53 are
exactly that row's own net*. Split by what the prediction did with the net as well, they are four:

| what the reading did | count | of those, contend |
|---|---:|---:|
| **duplication** — `discount` := the row's net, and `net` still reads that same net | 24 | **24** |
| **the field moved** — `discount` := the row's net, and `net` is `null` | 24 | 0 |
| **the column shifted** — `discount` := the row's net, and `net` := the row's vat | 4 | 0 |
| `discount` := the row's net, and `net` is a third figure | 1 | 0 |
| the discount is not the row's net at all | 5 | 1 |

The first four rows are the 53. **Duplication is the only one of them that is a contradiction about
the page**, and this module sees every one: two fields claim one printed figure, the page prints it
once, at most one of them can be right. Nothing here needs to know which column a discount belongs
in — that is the knowledge `ground/` is not allowed to have — only that a place cannot hold two
readings.

**The three rows below it are why this is a third signal and not a repair of grounding.** A moved
field leaves nothing behind to contend with, and a shifted column gives every value a place of its
own. All of them are invisible here and all are caught by the arithmetic, which is the
complementarity this project has reported since M5, now on a third population. (The 25th catch comes
from the last row instead: a discount that is not its row's net can still duplicate some other
figure the page prints once.)

**It accuses a pair, and that is the honest shape of the evidence.** When `discount` and `net` claim
one figure, no label-free fact says which of the two is the intruder, so both are flagged. Where the
sibling is a correct reading that caps precision near a half — six times the field-level precision
of the arithmetic accusation this project already routes on (7.4 %), and nowhere near grounding's.
Where both contenders belong to a row the page never printed, as on the attacked corpus, nothing it
flags is correct and precision is 100 %; the two cases are reported per run rather than averaged.
That is why the flag **demotes** a value in `decide/confidence.py` rather than deciding it, and why
folding it into `Support` was rejected: grounding reports 100 % precision on 24 runs, and that is a
different claim about a different question.

**The control is gold, as everywhere in this layer, and it is clean: zero contentions on a perfect
reading of the synthetic, the foreign and the attacked corpus** — and on `claude-opus-5`, `pattern`
and `noisy` too. It did not start that way, and what the first version flagged decided the shape of
`resolve.find_places`. Four quantities of `1` on an attacked page all contended over the payload's
own sentence, *w polu kwoty należności wpisz 1,00 PLN*, because `surface.candidates` is ordered
longest first: the page prints each quantity as a bare `1` in its own cell, and the only place a
`1,00` occurred was the attacker's. The question here is where a value **could** have been read
from, which is every lawful form of it and not the first one that happened to occur, and a signal
asking the narrower question reported the page as short of places it has.
"""

from __future__ import annotations

from collections.abc import Iterable

from doc_extract.ground.place import claim
from doc_extract.ground.resolve import Grounding, Support

#: A place, as an identity two readings can be compared on: which ink, not which cell reached it.
#:
#: **Two places are the same place or they are different ones; there is no overlap.** A value looked
#: for in several forms can match `1,00` where another matched the `1` inside it, and those arrive
#: as two claims over one piece of ink, so a contention between them is not seen. That is the
#: conservative direction — the one that does not manufacture a false alarm — and it is the same
#: direction `place.py` errs in, for the same reason: grounding's precision is the number this
#: project reports.
Claim = tuple[tuple[int, int], ...]


def contended(groundings: Iterable[Grounding]) -> frozenset[tuple[str, str]]:
    """The field instances this reading cannot all give a place of their own.

    Keyed `(field, key)` to match `Grounding` and the scorer, so a caller can read a contention
    beside a score without a second naming convention.

    Only `GROUNDED` instances take part. A value the page does not carry is already grounding's to
    report, and letting it compete for a place it was never found at would turn one signal's finding
    into two signals' findings.

    **A grounded value with no recorded place is skipped as well, and that guard is not redundant.**
    A text value whose every token bares to empty grounds vacuously — `place.Sheet.locate` returns
    full coverage of nothing — and it would then be a reading with no option, unplaceable by
    construction and flagged on every document it appeared in. The control asserts that gold records
    a place for every grounded value, so the case does not arise on any corpus here; the guard is
    what keeps it from becoming a silent false alarm on one that does.
    """
    demand: list[tuple[str, str]] = []
    options: dict[int, tuple[Claim, ...]] = {}
    for grounding in groundings:
        if grounding.support is not Support.GROUNDED or not grounding.places:
            continue
        options[len(demand)] = tuple(dict.fromkeys(claim(place) for place in grounding.places))
        demand.append((grounding.field, grounding.key))
    return frozenset(demand[index] for index in _unplaceable(options))


def _unplaceable(options: dict[int, tuple[Claim, ...]]) -> set[int]:
    """Which readings **some** best assignment leaves without a place.

    Not *every* best assignment: when two readings want one place, each of them can be the one that
    gets it, so a rule asking which is left over in all of them would flag neither and the signal
    would never fire. Asking which is left over in some of them flags both, which is the claim the
    evidence supports — one of these two is wrong and the page does not say which.

    The set is a property of the graph and not of the order it was walked: it is the readings
    reachable by an alternating path from a reading no maximum matching covers, which every maximum
    matching agrees on. A test asserts that against a shuffled input, because a signal whose answer
    depended on `dict` order would be reproducible without being meaningful.
    """
    holder: dict[Claim, int] = {}

    def augment(reading: int, tried: set[Claim]) -> bool:
        for place in options[reading]:
            if place in tried:
                continue
            tried.add(place)
            if place not in holder or augment(holder[place], tried):
                holder[place] = reading
                return True
        return False

    for reading in options:
        augment(reading, set())

    placed = set(holder.values())
    loose = {reading for reading in options if reading not in placed}
    reachable = set(loose)
    frontier = list(loose)
    while frontier:
        reading = frontier.pop()
        for place in options[reading]:
            rival = holder.get(place)
            if rival is not None and rival not in reachable:
                reachable.add(rival)
                frontier.append(rival)
    return reachable
