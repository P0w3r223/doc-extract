"""M5 — per-field confidence and accept / review / reject routing.

The runtime gate the project's first pillar promises: a document that breaks its own arithmetic, or
whose values are not on its own page, is routed rather than returned as a confident answer.

Nothing here consults the gold. `confidence.assess` reads a prediction against the source document
it came from, which is the only information a caller has at inference time. Whether the gate is any
good is a separate question, answered in `eval/selective.py` against gold, and answered as a
coverage-accuracy curve rather than a single number.
"""

from doc_extract.decide.confidence import (
    ROUTES,
    Assessment,
    Confidence,
    Route,
    assess,
    route,
)

__all__ = ["ROUTES", "Assessment", "Confidence", "Route", "assess", "route"]
