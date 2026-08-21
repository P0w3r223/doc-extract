"""M7 — the same page, seen through a scanner.

Every document this project has measured so far arrived as a PDF whose text layer reportlab wrote:
exact, complete, in the order the values were drawn. That is the last unearned advantage in the
corpus, and it is a large one. `claude-opus-5` reads all 108 documents perfectly, and the honest
reading of that result is not that extraction is solved but that reading a machine-generated text
layer was never the hard part.

An invoice in an accounts-payable inbox is frequently a picture. It was printed, signed, put on a
platen slightly crooked and emailed back as a JPEG inside a PDF, and there is no text layer at all —
`source/words.py` returns an empty tuple and everything above it returns nothing. That is not a
degraded version of this project's problem; for the text path it is the end of it.

So this package prints M2's pages and then **scans them**, at three rungs that each isolate one
thing (`rungs.py` states them). The gold does not move, the layout does not move, the vocabulary
does not move — the same discipline `foreign/` follows, applied to the other axis. What a run over
this corpus can answer that no earlier one could:

* how much of the text pipeline's accuracy was the text layer, measured rather than assumed;
* whether the signals the gate is built on survive a scan — **grounding cannot**, because it
  resolves a value to a span of page text and there is no page text, and neither can the place
  contention M7j added, for the same reason, so on a scanned document the gate is left with
  arithmetic alone;
* what a model reading the *image* recovers instead, which is the only reader left when the text
  layer is gone, and the one M7d puts a price on.

**The scanner is deliberately mild.** A rung that made the page illegible would measure the rung.
"""
