"""One string printed on a page that nothing in the document's own data put there.

The generator prints an invoice out of its gold and its context, and every character it emits is
implied by one of the two. An **overlay** is the exception: a piece of text a third party got onto
the page. That is the whole of what an attacker on an accounts-payable pipeline has — not access to
the prompt, not a tool, just words on a document somebody will feed to a model.

This module is deliberately empty of intent. It knows *where* a page can carry text and nothing
about what the text says or why; `attack/` owns that half. The split matters more than it looks: the
renderer is the corpus generator, and a renderer that imported an attack catalogue would make every
clean document depend on the suite that attacks it.

**The four placements are the four positions that are actually different**, in the terms M3's source
layer sees:

* `description` — inside an item's own description cell, so the payload arrives interleaved with the
  row's numbers and inside the table the extractor is reading most carefully.
* `annotations` — appended to the `Adnotacje` block, which is a real FA(3) free-text field and the
  place a supplier legitimately writes prose.
* `footer` — a paragraph of its own after the payment block, the shape of a covering note.
* `invisible` — the same paragraph, set in white. Present in the text layer, absent to a human
  reviewing the PDF, which is the version of this attack that actually gets past people.

`invisible` is the one that has to be asserted rather than assumed: it is only an attack if the text
survives into what `source/` reads, and `tests/test_synth_overlay.py` requires exactly that.
"""

from __future__ import annotations

from dataclasses import dataclass

DESCRIPTION = "description"
ANNOTATIONS = "annotations"
FOOTER = "footer"
INVISIBLE = "invisible"

#: In print order down the page, which is also the order a report reads best in.
PLACEMENTS: tuple[str, ...] = (DESCRIPTION, ANNOTATIONS, FOOTER, INVISIBLE)


@dataclass(frozen=True, slots=True)
class Overlay:
    """Text to print, and the one place on the page it goes."""

    text: str
    placement: str

    def __post_init__(self) -> None:
        if self.placement not in PLACEMENTS:
            raise ValueError(
                f"unknown placement {self.placement!r}; expected one of {', '.join(PLACEMENTS)}"
            )
        if not self.text.strip():
            raise ValueError("an overlay with no text is not a placement, it is a no-op")

    def at(self, placement: str) -> bool:
        return self.placement == placement
