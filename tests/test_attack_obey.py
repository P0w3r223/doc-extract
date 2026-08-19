"""The compliant control, and the property that makes it a control rather than a cheat.

`gullible` is allowed to read the corpus's own printed strings — the same licence `eval/pattern.py`
has and `extract/prompt.py` does not. What it is *not* allowed is to know which attack was on the
page: it finds the payload the way a model would, by reading. The test that matters is therefore the
negative one — on a page nobody attacked it finds nothing and answers the gold, so running it over
the clean corpus makes it B0 rather than a baseline with a secret.
"""

from __future__ import annotations

import pytest

from doc_extract.attack import obey
from doc_extract.attack.payloads import BY_NAME, PAYLOADS
from doc_extract.schema.ksef import Invoice
from doc_extract.source import document as source_document
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth import render
from doc_extract.synth.tiers import TIERS


@pytest.fixture(scope="module")
def clean_pages() -> tuple[str, ...]:
    """One page per layout, from three different tiers, with nothing injected into any of them."""
    documents = list(synth_corpus.documents(per_tier=1, tiers=TIERS[:3]))
    return tuple(source_document.read(render.render(doc).data).text for doc in documents)


def test_a_clean_page_carries_no_instruction(clean_pages: tuple[str, ...]) -> None:
    """The property the whole control rests on: no marker occurs in the corpus by accident."""
    for page in clean_pages:
        assert obey.instructions(page) == ()


def test_a_clean_page_is_answered_with_the_gold(invoice: Invoice, clean_pages) -> None:
    answer, notes = obey.obey(invoice, clean_pages[0])
    assert answer == invoice
    assert notes == ()


@pytest.mark.parametrize("payload", PAYLOADS, ids=lambda payload: payload.name)
def test_an_instruction_on_the_page_is_followed(payload, invoice: Invoice) -> None:
    answer, notes = obey.obey(invoice, f"Faktura VAT\n{payload.text}\nRazem 100,00")
    assert answer == payload.effect(invoice)
    assert len(notes) == 1
    assert notes[0].startswith(payload.name)


def test_a_wrapped_instruction_is_still_found(invoice: Invoice) -> None:
    """A renderer breaks a line where the column ends; that is not a change to the words."""
    payload = BY_NAME["total_override"]
    broken = payload.marker[:4] + "\n\t" + payload.marker[4:]
    assert BY_NAME["total_override"] in obey.instructions(f"Pozycje\n{broken}\n")


def test_a_refusal_ends_the_answer(invoice: Invoice) -> None:
    """Obeying "return nothing" leaves nothing for a later instruction to change."""
    page = BY_NAME["refusal"].text + "\n" + BY_NAME["total_override"].text
    answer, notes = obey.obey(invoice, page)
    assert answer is None
    #: The catalogue's order decides which fires first, and `total_override` precedes `refusal` —
    #: so the total is rewritten, then the answer is withdrawn, and the note trail says both.
    assert [note.split()[0] for note in notes] == ["total_override", "refusal"]
