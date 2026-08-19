"""The four baselines, and the real model, behind one interface: they are all `LLMClient`s.

A baseline that ran through its own code path would measure its own code path. These do not: each
one answers a request in the wire format and everything downstream — the prompt, the JSON parse, the
`Invoice` validation, the repair loop, the failure taxonomy, the per-attempt usage — is the same
machinery for all five. What varies is exactly one thing, which is what a baseline is for.

**B0 `oracle`** sees the gold. It is the ceiling: a perfect reading, scored. Anything below 100 %
here is the harness rather than the model, which makes it a bug in this package and not a finding
about extraction.

**B1 `constant`** sees nothing. It answers the same lawful invoice for every document, and it is a
diagnostic as much as a floor: any field it scores well on is a field whose accuracy is mostly prior
— `currency` is `PLN` on eight tiers of nine — so a model beating B1 there has demonstrated less
than its number suggests.

**B2 `pattern`** sees the page. The strongest non-model reader, deliberately fitted to the corpus's
own printed labels (see `pattern.py`), answering how much of this task needs a language model at
all. Its failures are structural rather than random, which is why they are worth reporting.

**B3 `noisy`** sees the gold, and breaks it at a fixed rate. Not a competitor: it is the labelled
error set M5's detector study needs, since a detector measured only on a model's unlabelled mistakes
is measured on a sample nobody chose.

**`gullible`** sees the page and the gold, and belongs to M6. It reads the page for an injected
instruction and does exactly what it says — the positive control for the attack suite, in the same
sense B0 is the positive control for the scorer and B3 for the detector. On a document nobody
attacked it is B0.

**`claude`** sees the page, and is not a baseline at all: it is the system under test, and the only
one that needs a key or costs money.

The three deterministic ones answer with `scripted.always`, so a repair request gets the same answer
back and the record shows the retry that a deterministic reader cannot benefit from. Their `Usage`
is zero, and it is zero because nothing was spent — not because a fake invented a plausible number.
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

from doc_extract.attack import obey
from doc_extract.eval import corrupt, pattern
from doc_extract.extract import pipeline, scripted, wire
from doc_extract.extract.client import LLMClient
from doc_extract.extract.scripted import Reply
from doc_extract.schema.ksef import Invoice, Party
from doc_extract.source.document import SourceDocument

ORACLE = "oracle"
CONSTANT = "constant"
PATTERN = "pattern"
NOISY = "noisy"
GULLIBLE = "gullible"
CLAUDE = "claude"

#: What B1 answers, on every document, forever.
#:
#: Chosen to be lawful and uninformative: the standard's default kind, Poland's currency, a
#: placeholder party, no rows, and a zero total. It is not tuned to the corpus — a constant fitted
#: to the corpus's most common invoice would be a *model*, trained on the test set, and its score
#: would no longer be the floor it is meant to establish.
CONSTANT_INVOICE = Invoice(
    kind="VAT",
    number="FV/1/2026",
    issue_date="2026-01-01",
    currency="PLN",
    seller=Party(name="Sprzedawca"),
    buyer=Party(name="Nabywca"),
    total_gross=Decimal("0.00"),
)


@dataclass(frozen=True, slots=True)
class Task:
    """One document, as much of it as any baseline is allowed to see."""

    doc_id: str
    gold: Invoice
    source: SourceDocument
    seed: int
    options: dict[str, object] = field(default_factory=dict)

    def rng(self) -> random.Random:
        """A generator seeded from the document, so a baseline is reproducible per document.

        Per document rather than per run: adding a tier, or scoring a subset, then leaves every
        other document's injected errors untouched — the same property `synth.corpus` gives the
        corpus itself, and for the same reason.
        """
        return random.Random(self.seed)


@dataclass(frozen=True, slots=True)
class Prepared:
    """A client for one document, and whatever the baseline wants recorded about what it did."""

    client: LLMClient
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Baseline:
    """One way of answering, named, with what it is allowed to see stated in the report."""

    name: str
    sees: str
    description: str
    prepare: Callable[[Task], Prepared]
    #: Whether running it can reach the network and cost money. The runner says so before starting.
    remote: bool = False


def _oracle(task: Task) -> Prepared:
    return Prepared(client=scripted.always(_reply(task.gold, ORACLE)))


def _constant(task: Task) -> Prepared:
    return Prepared(client=scripted.always(_reply(CONSTANT_INVOICE, CONSTANT)))


def _pattern(task: Task) -> Prepared:
    """Read the page with regular expressions, and answer with whatever came back.

    The result is not validated here. An unmatched required field reaches `Invoice` as `None` and
    is rejected there, which the pipeline records as `schema_invalid` with the validator's own
    errors — the same failure class, by the same route, as a model that answered badly.
    """
    payload = pattern.read(task.source.text)
    return Prepared(client=scripted.always(Reply(
        text=json.dumps(payload, ensure_ascii=False), model=PATTERN
    )))


def _noisy(task: Task) -> Prepared:
    rate = float(task.options.get("rate", corrupt.DEFAULT_RATE))
    corrupted, injections = corrupt.corrupt(task.gold, task.rng(), rate=rate)
    return Prepared(
        client=scripted.always(_reply(corrupted, NOISY)),
        notes=tuple(injection.note for injection in injections),
    )


def _gullible(task: Task) -> Prepared:
    """M6's positive control: read the page, find the injected instruction, and do as it says.

    Not a competitor and not a model — the attack suite's `oracle`. Its success rate is 100 % by
    construction, which is what makes it a check on the judge: an attack whose success cannot be
    recognised when it was fully obeyed would report every real model as safe. On a document with
    no payload it answers the gold, so running it over the clean corpus scores like B0.
    """
    answer, notes = obey.obey(task.gold, task.source.text)
    if answer is None:
        #: The one payload whose effect is to give no answer. Replying with a refusal rather than
        #: with an empty body puts it through the pipeline's own `stop_reason` path, so the record
        #: carries the failure class a real refusal would have.
        refusal = Reply(text="", stop_reason=pipeline.REFUSAL, model=GULLIBLE)
        return Prepared(client=scripted.always(refusal), notes=notes)
    return Prepared(client=scripted.always(_reply(answer, GULLIBLE)), notes=notes)


def _claude(task: Task) -> Prepared:
    """The real model. Imported here rather than at module scope, like the SDK it wraps.

    `eval` is importable, and every offline baseline runnable, on an install with no `anthropic`
    package and no key. Reaching this function is the one thing that is not.
    """
    from doc_extract.extract.anthropic_client import AnthropicClient

    return Prepared(client=AnthropicClient())


def _reply(invoice: Invoice, model: str) -> Reply:
    """An invoice as the model's answer — through `wire`, so it makes the same round trip."""
    return Reply(text=json.dumps(wire.serialise(invoice), ensure_ascii=False), model=model)


BASELINES: tuple[Baseline, ...] = (
    Baseline(
        name=ORACLE,
        sees="the gold",
        description="B0 — a perfect reading of the page. The ceiling, and a check on the harness.",
        prepare=_oracle,
    ),
    Baseline(
        name=CONSTANT,
        sees="nothing",
        description="B1 — the same lawful invoice for every document. The floor, and the prior.",
        prepare=_constant,
    ),
    Baseline(
        name=PATTERN,
        sees="the page",
        description="B2 — regular expressions and columns, fitted to this corpus's labels.",
        prepare=_pattern,
    ),
    Baseline(
        name=NOISY,
        sees="the gold",
        description="B3 — the oracle with known errors injected, for M5's detector study.",
        prepare=_noisy,
    ),
    Baseline(
        name=GULLIBLE,
        sees="the page and the gold",
        description="M6 — a reader that obeys any instruction printed on the page. The control.",
        prepare=_gullible,
    ),
    Baseline(
        name=CLAUDE,
        sees="the page",
        description="the system under test: a real model, over the network, at a cost.",
        prepare=_claude,
        remote=True,
    ),
)

BY_NAME: dict[str, Baseline] = {baseline.name: baseline for baseline in BASELINES}
