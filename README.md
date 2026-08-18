# doc-extract — invoice extraction that knows when it is wrong

Structured extraction from Polish invoices, built around a question most extraction projects skip:
**how do you know the output is right, on a document nobody annotated?**

An invoice answers that itself. Net plus VAT equals gross. Line items sum to their rate total. The
rate applied to the net gives the VAT. NIP and IBAN carry check digits. None of this needs a label,
a human, or a second model — it is arithmetic the issuer already performed, and it is available at
inference time on every document that arrives.

This project uses that redundancy three ways: as a **gate** (a document that fails is routed, not
returned), as a **measured detector** (does "invariants hold" actually predict "fields are
correct"?), and as the basis for a **coverage–accuracy trade-off** — how much can be processed
automatically, at what accuracy, if the rest goes to a human.

Target schema: **KSeF FA(3)**, the Polish national e-invoicing standard, mandatory since 2026.

## The gap this fills

The FA(3) XSD published by the Ministry of Finance contains **zero assertions**. It is XSD 1.0, so
it validates types, enumerations and cardinality — and nothing else. `P_15`, the gross total, is a
bare decimal with no stated relationship to the per-rate totals, and those have none to the line
items.

**The national standard defines the shape of an invoice and leaves every consistency rule
unenforced.** Checking those rules is therefore real work, not a re-run of validation that already
exists. The vendored schema is in `schemas/` with its provenance and SHA-256, so the claim is
checkable rather than asserted.

## Status — milestones 1–2 of 7

The domain layer and the corpus generator are complete. Both run with no model, no network and no
API key.

| | |
|---|---|
| `schema/vocab.py` | closed domains **generated from the vendored XSD**; a test re-derives them and fails on drift |
| `schema/checksums.py` | NIP, REGON (9 and 14 digit), IBAN mod-97 — total functions that return `False` rather than raising |
| `schema/ksef.py` | frozen Pydantic subset of FA(3); `extra="forbid"`, `Decimal` money, closed enums |
| `schema/invariants.py` | 15 rules across totals, lines, identifiers and dates, reported as data |
| `synth/` | KSeF-conformant XML **as the gold** → PDF, in 9 difficulty tiers × 3 layouts |
| tests | **198 passing**, ruff clean |

Milestones 3–7: extraction pipeline → scorer and baselines → the detector study and selective
prediction → prompt-injection suite → real held-out set and the reported synthetic↔real gap.

## The corpus

```bash
python -m doc_extract.synth --out data/synthetic     # 108 documents, ~6 MB, not committed
```

Ground truth and the rendered page come from **one artifact**: the generator writes a document that
validates against the vendored XSD, and the same file read back through the extraction schema *is*
the gold. There is no annotation step, so there is no annotation noise to confuse with model error
— which is what makes the detector study in milestone 5 interpretable at all. The round-trip is
required to be the identity, and it is a test.

Difficulty is a **controlled variable** rather than an unlabelled mixture, so accuracy can be
plotted against it:

| Tier | What it adds |
|---|---|
| `clean` | the control arm — one rate, whole quantities, round prices |
| `mixed_rates` | 23 / 8 / 5 % and an exempt position, four rate blocks to keep apart |
| `correction` | *korekta* with negative quantities and a reference to another invoice |
| `advance` | *zaliczka*: the amount is a part payment, and the order value is not the total |
| `reverse_charge` | zero VAT that is not a zero-rated sale |
| `split_payment` | the mandatory annotation and the account it must be paid to |
| `foreign_currency` | EUR with an NBP rate; the PLN figures on the page are not the invoice's |
| `grosz_rounding` | eight-decimal unit prices, so no line total is an exact product |
| `multi_page` | rows continuing past the totals onto a second page |

Every tier is rendered in all three layouts, so a per-tier result can never be a per-template one
in disguise. The corpus is a function of one integer: the seed is in the manifest, the bytes are
reproducible, and nothing is committed.

**What the synthetic corpus does not have** is real-world visual chaos — skew, stamps, poor scans,
layouts no template anticipated. Milestone 7's real held-out set exists to measure how much that
costs, and the gap will be reported whichever way it comes out.

## Two design decisions worth stating up front

**Invariants report; they do not raise.** A document whose numbers disagree must still be
constructible. Shape validation (types, decimal places, closed domains) raises, because a document
violating it is meaningless. Arithmetic goes through `invariants.check()`, which returns violations
as data carrying a stable rule id, a severity and the signed miss. A model that refused to
construct a broken invoice could not be routed, counted or explained — and inspecting broken
invoices is the whole project.

**Hard rules and heuristics are kept apart.** `Severity.HARD` is an arithmetic identity: a
violation means something is genuinely wrong. `Severity.HEURISTIC` usually holds but has lawful
exceptions — an invoice may legitimately be issued up to 60 days before the sale it documents.
Mixing them would blunt the detector, because a heuristic's false positives would be
indistinguishable from a real arithmetic miss.

## What this cannot tell you

A check digit rules out corruption, not fabrication: it proves a NIP was not misread, never that it
exists or belongs to the named party. An extraction wrong in a way arithmetic cannot see passes
every rule silently. **Measuring exactly how often that happens is the point of milestone 5**, and
the number will be published whichever way it comes out.

## Running it

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Windows
pytest
ruff check .
```

## Licence

MIT.
