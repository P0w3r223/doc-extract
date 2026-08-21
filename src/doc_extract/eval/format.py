"""How a rate is written down. One implementation, because three would drift.

Two rules, and the second exists because this package got it wrong and a table caught it:

* **An absent denominator prints as `—`, never as `0 %`.** `aggregate` and every study here return
  `None` when there was nothing to divide by, and a renderer that coerced it would put a
  measurement in the table that nobody made.

* **`100 %` means exactly 100 %.** At one decimal place, 5234 correct out of 5236 prints as
  `100.0 %` — beside a column saying two wrong values were accepted. A reader is entitled to read
  a perfect score as perfect, so the precision grows until the number stops claiming to be one.
"""

from __future__ import annotations

DASH = "—"

#: Decimal places to try, in order. Three is enough to separate one error in ten thousand, which is
#: finer than any denominator in this project.
_PLACES = (1, 2, 3)


def rate(value: float | None) -> str:
    """A percentage, or a dash when there was no denominator."""
    if value is None:
        return DASH
    if value >= 1.0:
        return "100 %"

    percent = value * 100
    for places in _PLACES:
        text = f"{percent:.{places}f}"
        if text != "100." + "0" * places:
            return f"{text} %"
    #: Closer to 1.0 than three places can show, and genuinely not 1.0. Say so rather than round.
    return "< 100 %"
