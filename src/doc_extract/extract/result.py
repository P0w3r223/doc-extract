"""What an extraction attempt produced, in the shape M4's metric rules require it to be recorded.

Three of those rules land here rather than under `eval/`, because a scorer cannot report what the
pipeline never kept:

* **A failure class and a `stop_reason` per prediction.** "It didn't work" is not a finding; "the
  model was truncated on the multi-page tier and refused on none of it" is. The classes are
  deliberately few and mutually exclusive, so a per-class count is a partition of the failures
  rather than an overlapping tally.
* **Cost over all attempts, including retries.** `Extraction.usage` sums every attempt, the failed
  ones included. Reporting only the successful call would make a pipeline that repairs half its
  documents look as cheap as one that never does.
* **Separate budgets per stage.** Each `Attempt` records which stage it was, so "ran out of tokens"
  can be attributed to extraction or to repair instead of to one undifferentiated budget.

Nothing here judges correctness. `succeeded` means a well-formed `Invoice` came back — not a right
one; that is M4's question, and `invariants` already has an opinion the pipeline does not consult.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from doc_extract.extract.client import Usage
from doc_extract.schema.ksef import Invoice


class Stage(StrEnum):
    """Which call this was. The two carry different token budgets and different prompts."""

    EXTRACT = "extract"
    REPAIR = "repair"


class FailureClass(StrEnum):
    """Why an attempt did not yield an invoice. Exactly one applies to any attempt."""

    NONE = "none"
    #: The request never reached an answer: no network, no key, a rejected payload.
    CLIENT_ERROR = "client_error"
    #: The model declined. A content outcome, not an error — and not something a repair can fix.
    REFUSED = "refused"
    #: Generation hit the token ceiling. The body is a prefix of an answer, so it is not repairable
    #: within a smaller repair budget; it is a signal that the budget was wrong.
    TRUNCATED = "truncated"
    #: The model stopped normally and said nothing.
    EMPTY = "empty"
    #: The body is not the JSON object the schema asked for.
    MALFORMED_JSON = "malformed_json"
    #: Well-formed JSON that `Invoice` refuses: a closed domain broken, a decimal place too many,
    #: a required field absent. The one failure a repair attempt exists for.
    SCHEMA_INVALID = "schema_invalid"


#: Failures a second attempt could plausibly fix, given the validator's own errors to work from.
REPAIRABLE = frozenset({FailureClass.MALFORMED_JSON, FailureClass.SCHEMA_INVALID})


@dataclass(frozen=True, slots=True)
class Attempt:
    """One call to the model, whatever came of it."""

    stage: Stage
    model: str
    stop_reason: str
    usage: Usage
    failure: FailureClass
    detail: str = ""


@dataclass(frozen=True, slots=True)
class Extraction:
    """One document's prediction: the invoice if there is one, and the record of getting there."""

    invoice: Invoice | None
    attempts: tuple[Attempt, ...]

    @property
    def succeeded(self) -> bool:
        return self.invoice is not None

    @property
    def failure(self) -> FailureClass:
        """The last attempt's class — `NONE` when one succeeded, since the last attempt is it."""
        return self.attempts[-1].failure if self.attempts else FailureClass.CLIENT_ERROR

    @property
    def usage(self) -> Usage:
        """Every attempt's tokens, not the winning one's."""
        return sum((attempt.usage for attempt in self.attempts), Usage())

    @property
    def repairs(self) -> int:
        return sum(1 for attempt in self.attempts if attempt.stage is Stage.REPAIR)
