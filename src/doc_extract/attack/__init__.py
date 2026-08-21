"""M6 — the invoice treated as what it is: input an adversary can write.

M5 asked whether a document's own arithmetic predicts that it was read correctly, on a population of
**model errors**. This package asks the other question, on a population of **attacks**: when someone
who wants the payment redirected can print a sentence on the page, what happens?

The three pieces are deliberately separate, because they answer to different owners:

* `payloads.py` — what an attacker writes, what obeying it looks like, and what counts as success.
* `suite.py` — the attacked corpus: the same invoices, one string added, gold untouched.
* `outcome.py` / `report.py` — the join between a prediction file and the grid that produced it,
  and the attack success rate that falls out of it, crossed with what M5's gate did about it.

The gold of an attacked document is the gold of the document it was made from. That single decision
is what lets every M4 and M5 measurement run over this corpus unchanged — accuracy, the detector,
the coverage-accuracy curve — so the suite adds a reading rather than a second pipeline.

Extraction holds lethal-trifecta leg **[A]** only: untrusted input, no sensitive systems, no egress.
The defences being measured are structural — a fixed stage order that never branches on document
content, a fence whose marker is derived from the text it wraps, an instruction to transcribe rather
than compute — and the point of measuring them is that a defence nobody attacked is a claim.
"""
