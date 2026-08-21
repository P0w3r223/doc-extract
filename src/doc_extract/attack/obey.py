"""The compliant reader: a model that does whatever the page tells it to.

Every measurement in this project has a control that establishes its instrument works before the
instrument is pointed at anything interesting. `oracle` does it for the scorer — 100 %, so anything
below that is the harness. `noisy` does it for the detector — known errors, so a recall is measured
against a population somebody chose. This is the one for the attack suite.

**It is a positive control, not a competitor.** It reads the page, finds any payload whose marker is
printed on it, and returns the answer that payload asked for. Its attack success rate is therefore
100 % by construction, and that is exactly the number it is for: if `outcome.py` scored it below
100 %, the fault would be in the judge rather than in any model — a payload whose success cannot be
recognised even when it is fully obeyed would report every real model as safe.

It finds payloads the way `eval/pattern.py` finds fields: by matching strings the corpus prints. The
comparison ignores whitespace, because a renderer wraps where a column ends and M3's layout reader
joins cells with tabs, and neither changes the words. That is a licence this module has and
`extract/prompt.py` does not — the same split the project already draws between a baseline that may
know the corpus's labels and a prompt that may not.

It never sees the assignment file. A control that was *told* which attack was on the page would be
testing the join rather than the page, and the join is the thing it is meant to check.
"""

from __future__ import annotations

from doc_extract.attack.payloads import PAYLOADS, Payload
from doc_extract.schema.ksef import Invoice


def instructions(page_text: str) -> tuple[Payload, ...]:
    """Every payload whose marker is printed on this page, in catalogue order."""
    squeezed = _squeezed(page_text)
    return tuple(payload for payload in PAYLOADS if _squeezed(payload.marker) in squeezed)


def obey(gold: Invoice, page_text: str) -> tuple[Invoice | None, tuple[str, ...]]:
    """The answer a fully compliant reader gives, and a note per instruction it followed.

    Applied in catalogue order, so two payloads on one page compose deterministically. A payload
    whose effect is to give no answer ends it: a reader that has refused has nothing further to say,
    and continuing to apply changes to an answer it never returns would be recording an intent
    rather than an outcome.
    """
    answer: Invoice | None = gold
    notes: list[str] = []
    for payload in instructions(page_text):
        if answer is None:
            break
        answer = payload.effect(answer)
        notes.append(_note(payload, answer))
    return answer, tuple(notes)


def _note(payload: Payload, answer: Invoice | None) -> str:
    """What the prediction file records. Flat text with the payload name first, like `corrupt`."""
    if answer is None:
        return f"{payload.name} declined: {payload.goal}"
    if payload.harmless:
        return f"{payload.name} no-op: {payload.goal}"
    return f"{payload.name} obeyed: {payload.goal}"


def _squeezed(text: str) -> str:
    return "".join(text.split())
