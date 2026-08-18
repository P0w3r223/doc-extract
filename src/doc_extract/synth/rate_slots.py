"""Which `P_13_x` / `P_14_x` block of FA(3) each VAT rate is summed into.

This sits in its own module because two things need it and neither should import the other: the
builder, to put an invoice's rate totals in the order the standard lists them, and the writer, to
place them in a sequence XSD 1.0 requires to be ordered.

**One rate pair cannot round-trip, and the generator refuses it.** `P_13_1` is "the standard rate"
and carries 23 % or the historical 22 % without recording which; `P_13_2` merges 8 % with 7 % the
same way. A document written into those blocks could not be read back unambiguously, so gold built
from it would be a guess. The historical members are therefore never emitted — see `AMBIGUOUS`.
"""

from __future__ import annotations

from typing import Final

#: Rate code -> the net element and the tax element carrying it. Untaxed codes have a net block and
#: no tax block at all in the standard, which is what the `None` records.
SLOTS: Final[dict[str, tuple[str, str | None]]] = {
    "23": ("P_13_1", "P_14_1"),
    "8": ("P_13_2", "P_14_2"),
    "5": ("P_13_3", "P_14_3"),
    "4": ("P_13_4", "P_14_4"),
    "0 KR": ("P_13_6_1", None),
    "0 WDT": ("P_13_6_2", None),
    "0 EX": ("P_13_6_3", None),
    "zw": ("P_13_7", None),
    "np I": ("P_13_8", None),
    "np II": ("P_13_9", None),
    "oo": ("P_13_10", None),
}

#: Codes that share a block with another code, and so cannot be recovered from the document.
AMBIGUOUS: Final = frozenset({"22", "7", "3"})

#: The order `Fa` requires its children to appear in. XSD 1.0 sequences are ordered: this is a
#: constraint of the standard, not a formatting preference.
FA_ORDER: Final = (
    "KodWaluty", "P_1", "P_1M", "P_2",
    "P_13_1", "P_14_1", "P_14_1W",
    "P_13_2", "P_14_2", "P_14_2W",
    "P_13_3", "P_14_3", "P_14_3W",
    "P_13_4", "P_14_4", "P_14_4W",
    "P_13_5", "P_14_5",
    "P_13_6_1", "P_13_6_2", "P_13_6_3",
    "P_13_7", "P_13_8", "P_13_9", "P_13_10", "P_13_11",
    "P_15",
)

SLOT_TO_RATE: Final = {net_tag: rate for rate, (net_tag, _) in SLOTS.items()}


def order_of(rate: str) -> int:
    """Where a rate's block falls in `Fa` — the order an invoice's totals must be listed in.

    The builder sorts by this so the gold matches the document rather than the order rows happened
    to be drawn in; without it the round-trip would fail on every mixed-rate invoice.
    """
    return FA_ORDER.index(SLOTS[rate][0])
