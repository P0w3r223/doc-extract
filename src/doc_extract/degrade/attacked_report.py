"""Which channel each payload reached its reader by, as Markdown. Formatting only.

It is a section rather than a report of its own because it is a **qualification on somebody else's
number**. An attack success rate of zero on a rung where no payload reached the model at all is a
measurement of a blind reader, and a reader who meets that fact after the table has already read the
table. `attack/report.py` takes it as a `preamble` and prints it above everything.

The table's unit is a `(placement, rung)` cell, because that is what the two channels are a property
of: a payload's text is the same string in all four placements, and what differs is where it was
printed and what the scanner then did to the page. The payload column would be four copies of one
row.
"""

from __future__ import annotations

from collections.abc import Sequence

from doc_extract.degrade.attacked import Reach
from doc_extract.eval.format import DASH

#: What a cell says, in the order it degrades. `text + image` is a payload a text pipeline and a
#: vision model can both read; `image only` is one only a vision model can; `nobody` is one the page
#: no longer carries at all.
BOTH = "text + image"
IMAGE_ONLY = "image only"
TEXT_ONLY = "text only"
NOBODY = "**nobody**"

#: A cell whose documents do not agree. Reported rather than resolved — see `channel`.
MIXED = "mixed"


def render(reaches: Sequence[Reach], *, reads_images: bool = False) -> str:
    """The reach table and the sentences that say what it does to the rates below it.

    `reads_images` says which of the two columns is the one that matters for the run being
    reported. A text pipeline is stopped by a missing text layer and can be attacked by nothing
    else; a model sent the page as an image is stopped only by ink that left no mark. Printing
    both readings unconditionally would put the wrong caveat above two thirds of a vision run's
    numbers — "no payload reached the text layer" is true there and beside the point.
    """
    if not reaches:
        return ""
    placements = _ordered(row.placement for row in reaches)
    rungs = _ordered(row.rung for row in reaches)
    cells = {
        (placement, rung): [
            row for row in reaches if row.placement == placement and row.rung == rung
        ]
        for placement in placements
        for rung in rungs
    }
    return "\n".join([
        "## Which channel the payload reached the reader by",
        "",
        *_findings(reaches, rungs=rungs, reads_images=reads_images),
        "",
        "Measured at build time with no model involved. **text** means the marker is in the text "
        "layer `source/` reads off the scanned page; **image** means the attacked page and the "
        "unattacked page it was made from differ as pictures, through the same scanner at the same "
        "seed — so a payload that changed no pixel cannot be seen by any reader that looks at the "
        "page.",
        "",
        "| placement | " + " | ".join(f"`{rung}`" for rung in rungs) + " |",
        "|---|" + "---|" * len(rungs),
        *(
            f"| `{placement}` | "
            + " | ".join(channel(cells[(placement, rung)]) for rung in rungs)
            + " |"
            for placement in placements
        ),
    ])


def channel(rows: Sequence[Reach]) -> str:
    """What a group of rows says about the channel its payload came through.

    The one place the classification lives. `docs/build_index.py` renders the same table on the
    site and calls this rather than re-deriving it: a second implementation of a rule is the
    failure a page of derived figures is most exposed to, and this project has caught one before.

    Mixed answers are reported as mixed rather than resolved. A cell whose documents disagree is
    telling you the placement is not the only thing deciding, and averaging it into a third value
    would hide that.
    """
    if not rows:
        return DASH
    channels = {(row.in_text_layer, row.on_the_image) for row in rows}
    if len(channels) > 1:  # pragma: no cover — a placement behaves the same on every document
        return f"{MIXED} ({len(rows)})"
    in_text, on_image = channels.pop()
    if in_text and on_image:
        return BOTH
    if on_image:
        return IMAGE_ONLY
    if in_text:
        return TEXT_ONLY
    return NOBODY


def _findings(
    reaches: Sequence[Reach], *, rungs: Sequence[str], reads_images: bool = False
) -> list[str]:
    """The sentences the table is worth printing for, each stated only when it is true.

    The first one is about the channel the *reported run* actually read by, which is why it is not
    the same sentence in both modalities. A blind rung is a hole in a text pipeline's coverage and
    nothing at all to a model looking at the page.
    """
    lines = []
    blind = [
        rung for rung in rungs
        if not any(row.in_text_layer for row in reaches if row.rung == rung)
    ]
    if blind and reads_images:
        #: The text column is still printed — it is what a *text* run on this same corpus would
        #: have been limited by, and the two runs are meant to be read against each other.
        lines.append(
            f"* **This run read the page as an image, so the text layer is not its limit.** The "
            f"`image` column is: a payload that changed no pixel is unreachable here no matter "
            f"what the text column says, and a payload that did change one is on the page in front "
            f"of the model at every rung — including {_names(blind)}, where a text pipeline sees "
            "nothing at all. Read a zero below against the `image` column, not the `text` one."
        )
    elif blind:
        lines.append(
            f"* **No payload reached the text layer on {_names(blind)}.** Nothing did: the page "
            "carries no text at all. Every attack success rate below for those rungs is therefore "
            "a measurement of a reader that could not read the document, and it is **not** "
            "evidence of a defence. Whatever the `image` column marks is still on the page as ink "
            "at those rungs — whether a model reading pixels recovers it at 150 dpi through blur "
            "and JPEG is a different question, and a vision arm is what answers it."
        )
    #: Every row of the placement, not any of them. A placement erased at one rung and surviving at
    #: another belongs in neither list, and a version keyed on `any` would name it in both halves
    #: of the same sentence.
    by_placement = {
        placement: [row for row in reaches if row.placement == placement]
        for placement in _ordered(row.placement for row in reaches)
    }
    erased = tuple(
        placement for placement, rows in by_placement.items()
        if all(row.reaches_nobody for row in rows)
    )
    kept = tuple(
        placement for placement, rows in by_placement.items()
        if not any(row.reaches_nobody for row in rows)
    )
    if erased:
        lines.append(
            f"* **The scanner erases {_names(erased)} outright**, at every rung, while ink "
            "survives everywhere it was printed"
            + (f" ({_names(kept)})" if kept else "")
            + ". White text on "
            "white paper contributes no pixel, so there is nothing for a recogniser to recover and "
            "nothing for a vision model to read — the attack that was designed to be invisible to "
            "the human approving the invoice is the one a photocopier destroys. It is an accident "
            "of the medium and not a control: nothing in this repository chose it, and it protects "
            "only the placement that hides from a person."
        )
    return lines


def _names(values: Sequence[str]) -> str:
    quoted = [f"`{value}`" for value in values]
    if len(quoted) == 1:
        return quoted[0]
    return ", ".join(quoted[:-1]) + f" and {quoted[-1]}"


def _ordered(values) -> tuple[str, ...]:
    """Distinct values in first-seen order, which is the order the corpus was planned in."""
    seen: dict[str, None] = {}
    for value in values:
        seen.setdefault(value, None)
    return tuple(seen)


def summary_lines(reaches: Sequence[Reach]):
    """What a terminal wants after a build or a run, without the table."""
    if not reaches:
        return
    yield (
        f"reach      : text {sum(1 for row in reaches if row.in_text_layer)}   "
        f"image {sum(1 for row in reaches if row.on_the_image)}   "
        f"nobody {sum(1 for row in reaches if row.reaches_nobody)}   "
        f"of {len(reaches)}"
    )
