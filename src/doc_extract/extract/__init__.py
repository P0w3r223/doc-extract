"""Extraction: a source document in, a candidate `Invoice` — or a named failure — out.

The pipeline has a **fixed stage order** and no branch that lets document text reach a position of
authority: source text is sealed by `source.envelope`, the system prompt is a constant, the model
answers in a schema this package owns, and a reply that does not fit that schema is repaired at most
`max_repairs` times with the validator's own errors, never with the model's prose.

Nothing here decides whether an extraction is *correct*. `schema.invariants` already reports what an
invoice's arithmetic says about itself, and M5 turns that into a routing decision; M4 scores fields
against gold. What this package guarantees is narrower and worth stating plainly: whatever comes
back is either a well-formed `Invoice` or a failure with a class, a `stop_reason` and the token
usage of **every** attempt including the ones that failed.
"""
