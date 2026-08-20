"""The reach table, and the two sentences it exists to license.

Both sentences are conditional and both have to stay conditional. "No payload reached the text
layer" is a statement about a corpus that lost its text layer, and a version that printed it
unconditionally would put it on M6's unscanned corpus, where the opposite is true. The same goes for
the erasure sentence: it is the finding on this corpus and a falsehood on the one before it.
"""

from __future__ import annotations

import pytest

from doc_extract.degrade import attacked_report
from doc_extract.degrade.attacked import Reach


def _reach(placement: str, rung: str, *, text: bool, image: bool) -> Reach:
    return Reach(
        doc_id=f"payload-{placement}-00-{rung}",
        payload="total_override",
        placement=placement,
        rung=rung,
        in_text_layer=text,
        on_the_image=image,
    )


#: What the composed corpus actually measures: ink survives as pixels everywhere and as text only
#: where a text layer does, and white ink survives nowhere.
SCANNED = [
    _reach("footer", "searchable", text=True, image=True),
    _reach("footer", "rasterised", text=False, image=True),
    _reach("invisible", "searchable", text=False, image=False),
    _reach("invisible", "rasterised", text=False, image=False),
]

#: M6's corpus, where nothing was scanned: every payload is in the text layer, white ink included.
UNSCANNED = [
    _reach("footer", "classic", text=True, image=True),
    _reach("invisible", "classic", text=True, image=False),
]


def test_a_corpus_that_was_never_scanned_gets_no_section() -> None:
    """`attack/report.py` inserts whatever this returns; an empty string inserts nothing."""
    assert attacked_report.render([]) == ""


def test_the_table_names_a_channel_per_cell() -> None:
    body = attacked_report.render(SCANNED)

    assert f"| `footer` | {attacked_report.BOTH} | {attacked_report.IMAGE_ONLY} |" in body
    assert f"| `invisible` | {attacked_report.NOBODY} | {attacked_report.NOBODY} |" in body


def test_a_rung_with_no_text_layer_is_called_blindness_rather_than_a_defence() -> None:
    body = attacked_report.render(SCANNED)

    assert "No payload reached the text layer on `rasterised`" in body
    assert "not** evidence of a defence" in body


def test_the_erased_placement_is_named_and_the_surviving_ones_are_too() -> None:
    body = attacked_report.render(SCANNED)

    assert "erases `invisible` outright" in body
    assert "`footer`" in body


def test_neither_sentence_is_printed_where_it_would_be_false() -> None:
    """On M6's corpus the payload is in the text layer everywhere, white ink included."""
    body = attacked_report.render(UNSCANNED)

    assert "reached the text layer" not in body
    assert "erases" not in body
    assert f"| `invisible` | {attacked_report.TEXT_ONLY} |" in body


@pytest.mark.parametrize("reaches,expected", [
    (SCANNED, "text 1   image 2   nobody 2   of 4"),
    ([], None),
])
def test_the_terminal_summary_counts_each_channel(reaches, expected) -> None:
    lines = list(attacked_report.summary_lines(reaches))

    if expected is None:
        assert lines == []
    else:
        assert lines == [f"reach      : {expected}"]
