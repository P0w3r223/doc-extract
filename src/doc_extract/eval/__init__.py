"""Measurement: what a prediction got right, over how many documents, at what cost.

Nothing in this package calls a model, and nothing in it decides anything. A prediction arrives as
an `extract.result.Extraction` — an `Invoice` or a named failure, with the usage of every attempt —
and leaves as counts that a reader can check. The split is deliberate: `run` performs I/O and
records what happened, `scorer` and `aggregate` are pure functions over data already on disk, so a
number in the report can be recomputed from the committed prediction files without re-running
anything that costs money.

The nine metric rules this package exists to obey are in `CLAUDE.md`. Three of them shape the code
here rather than merely being followed by it:

* **Support is reported per field, and a metric with no support is `None`.** Not `0.0`, and not
  `1.0`. A field the corpus never carries has no accuracy, and printing one would invent a
  measurement out of an empty denominator.
* **Detection and value accuracy are separate questions.** "The field was found" and "the field was
  read correctly" fail for different reasons and are fixed by different work, so `Tally` reports
  both and never averages them into one number.
* **Coverage is asserted before scoring.** `score` compares the documents it was given against the
  documents the corpus manifest attests to, and refuses to report unless they match or the caller
  says in writing that a subset is intended — in which case the report says so too.

Field instances are matched by **key**, never by position: a line item by its printed number, a rate
block by its rate code. A prediction that emits the rows in a different order is not thereby wrong,
and a prediction that misreads a row's number is wrong in a way the report can name — the row it
claims is spurious and the row it missed is missing.
"""
