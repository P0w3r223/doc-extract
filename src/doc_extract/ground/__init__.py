"""M5 — value to source span provenance: did this figure actually come off the page?

`eval/detector.py` measures the arithmetic invariants as an error detector and finds a clean split:
on a real model's mistakes they catch every arithmetic error and none of the textual ones. Every
false negative there is a misread name or description — fields with no redundancy behind them.

This package is the complement to that, built because the measurement asked for it. `surface`
renders a normalised value back into the forms a Polish invoice could have printed it in; `resolve`
decides how much of each extracted value is actually on the page, and where.

Neither module may know what `synth/render.py` prints. Grounding matches **values**, never labels.
"""

from doc_extract.ground.resolve import Grounding, Support, resolve
from doc_extract.ground.surface import candidates

__all__ = ["Grounding", "Support", "candidates", "resolve"]
