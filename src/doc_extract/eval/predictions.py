"""The prediction file: one line per document, enough to recompute every number without the model.

The metric rules ask for a failure class and a `stop_reason` per prediction and for the prediction
files to be committed. This is that file. It is JSONL for the same reason the corpus manifest is —
one shape per line, appendable, diffable, and readable by anything — and it is written *before*
anything is scored, so a run that dies in the scorer has still recorded what the model said.

**A prediction records the bytes it was made from.** `pdf_sha256` is copied out of the corpus
manifest, so a report can prove it was computed on the corpus it names rather than on whatever
happened to be in `data/synthetic` at the time. Changing a font or the reportlab major regenerates
every page and every hash — which is precisely the change a stale prediction file would otherwise
survive unnoticed.

**Every attempt is kept, not just the last.** A repaired document has two attempts here, and the
failed one carries its own tokens. Reporting cost over the successful call alone would make a
pipeline that repairs half its documents look as cheap as one that never does.

**`notes` is where a baseline says what it did to the document.** The noisy oracle injects known
errors, and the detector study in M5 needs to know which ones: its whole question is whether the
invariants fire on the documents where something is actually wrong, and that requires the errors to
be recorded at the moment they were made rather than inferred afterwards from a diff.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from doc_extract.extract import wire
from doc_extract.extract.client import Usage
from doc_extract.extract.result import Attempt, Extraction, FailureClass, Stage
from doc_extract.schema.ksef import Invoice

PREDICTIONS_NAME = "predictions.jsonl"
RUN_NAME = "run.meta.json"
REPORT_NAME = "report.md"


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    """One call to the model, in the shape that survives a round trip through JSON."""

    stage: str
    model: str
    stop_reason: str
    failure: str
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    detail: str = ""

    @property
    def usage(self) -> Usage:
        return Usage(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cache_creation_input_tokens=self.cache_creation_input_tokens,
            cache_read_input_tokens=self.cache_read_input_tokens,
        )


@dataclass(frozen=True, slots=True)
class Prediction:
    """What one document produced: the invoice if there is one, and how it was arrived at."""

    doc_id: str
    tier: str
    template: str
    pdf_sha256: str
    failure: str
    stop_reason: str
    attempts: tuple[AttemptRecord, ...]
    invoice: dict[str, Any] | None = None
    #: What the baseline did to this document, if anything — the injected errors of the noisy
    #: oracle, empty for every baseline that only reads.
    notes: tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.invoice is not None

    @property
    def usage(self) -> Usage:
        return sum((attempt.usage for attempt in self.attempts), Usage())

    @property
    def repairs(self) -> int:
        return sum(1 for attempt in self.attempts if attempt.stage == Stage.REPAIR)

    def parse(self) -> Invoice | None:
        """The recorded invoice, back as the model this project scores against.

        Validated rather than trusted: a prediction file is an artifact on disk, and an artifact on
        disk is untrusted input like any other. This is also what makes the file replayable — the
        payload is the wire shape, so it goes back through the same validator the pipeline used.
        """
        return None if self.invoice is None else Invoice.model_validate(self.invoice)


@dataclass(frozen=True, slots=True)
class RunMeta:
    """What produced a set of predictions — the header a report has to be able to state.

    `corpus` carries the generator's own provenance block verbatim (seed, tier set, package
    versions, XSD and font hashes) rather than a summary of it. A metric is only comparable with
    another metric computed on the same corpus, and "the same corpus" is exactly what that block
    says.
    """

    baseline: str
    model: str
    corpus_dir: str
    documents: int
    max_tokens: int
    repair_max_tokens: int
    max_repairs: int
    effort: str | None = None
    started_at: str = ""
    corpus: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


def record(
    extraction: Extraction,
    *,
    doc_id: str,
    tier: str,
    template: str,
    pdf_sha256: str,
    notes: Sequence[str] = (),
) -> Prediction:
    """An `Extraction` as the row that goes on disk."""
    return Prediction(
        doc_id=doc_id,
        tier=tier,
        template=template,
        pdf_sha256=pdf_sha256,
        failure=str(extraction.failure),
        stop_reason=extraction.attempts[-1].stop_reason if extraction.attempts else "",
        attempts=tuple(_attempt(attempt) for attempt in extraction.attempts),
        invoice=wire.serialise(extraction.invoice) if extraction.invoice is not None else None,
        notes=tuple(notes),
    )


def _attempt(attempt: Attempt) -> AttemptRecord:
    return AttemptRecord(
        stage=str(attempt.stage),
        model=attempt.model,
        stop_reason=attempt.stop_reason,
        failure=str(attempt.failure),
        input_tokens=attempt.usage.input_tokens,
        output_tokens=attempt.usage.output_tokens,
        cache_creation_input_tokens=attempt.usage.cache_creation_input_tokens,
        cache_read_input_tokens=attempt.usage.cache_read_input_tokens,
        detail=attempt.detail,
    )


def write(predictions: Iterable[Prediction], path: Path) -> int:
    """Write the rows, returning how many. Bytes, not text — a corpus artifact is not CRLF."""
    rows = list(predictions)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        "".join(json.dumps(asdict(row), ensure_ascii=False) + "\n" for row in rows).encode("utf-8")
    )
    return len(rows)


def read(path: Path) -> tuple[Prediction, ...]:
    """Read a prediction file back, with amounts still exact."""
    return tuple(_prediction(row) for row in _rows(path))


def _rows(path: Path) -> Iterator[Mapping[str, Any]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            #: The payload holds money as strings, so this is belt and braces — and cheap. A file
            #: hand-edited into JSON numbers would otherwise round-trip through a float here, in
            #: the one place that reads a metric's input back off disk.
            yield json.loads(line, parse_float=str)


def _prediction(row: Mapping[str, Any]) -> Prediction:
    return Prediction(
        doc_id=row["doc_id"],
        tier=row["tier"],
        template=row["template"],
        pdf_sha256=row["pdf_sha256"],
        failure=row["failure"],
        stop_reason=row["stop_reason"],
        attempts=tuple(AttemptRecord(**attempt) for attempt in row["attempts"]),
        invoice=row.get("invoice"),
        notes=tuple(row.get("notes", ())),
    )


def write_meta(meta: RunMeta, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(asdict(meta), ensure_ascii=False, indent=2) + "\n"
    path.write_bytes(body.encode("utf-8"))


def read_meta(path: Path) -> RunMeta:
    return RunMeta(**json.loads(path.read_text(encoding="utf-8")))


def failure_of(prediction: Prediction) -> FailureClass:
    """The recorded class, back as the enum. Unknown values are refused rather than coerced."""
    return FailureClass(prediction.failure)
