# doc-extract

[![CI](https://github.com/P0w3r223/doc-extract/actions/workflows/ci.yml/badge.svg)](https://github.com/P0w3r223/doc-extract/actions/workflows/ci.yml)

**Structured extraction from Polish KSeF e-invoices, using the invoice's own arithmetic as an error
detector that needs no labels.**

The hard question in document extraction is how to know an output is right on a document nobody
annotated. An invoice answers part of it. Net plus VAT equals gross, line items add up to their rate
totals, the rate applied to the net gives the VAT, and NIP and IBAN carry check digits. The issuer
already did this arithmetic, so it is there at inference time on every incoming document.

The project uses those rules three ways: as a gate (a document that breaks them goes to a person
instead of being returned), as a detector whose value is measured (do the rules holding predict the
fields being right?), and as a coverage and accuracy trade-off (how much can be accepted
automatically, and how accurately).

Target schema: KSeF FA(3), the Polish national e-invoicing standard, mandatory since 2026.

## The gap this fills

The FA(3) XSD published by the Ministry of Finance contains **zero assertions**. It is XSD 1.0, so
it validates types, enumerations and cardinality — and nothing else. `P_15`, the gross total, is a
bare decimal with no stated relationship to the per-rate totals, and those have none to the line
items.

**The national standard defines the shape of an invoice and leaves every consistency rule
unenforced.** Checking those rules is therefore real work, not a re-run of validation that already
exists. The vendored schema is in `schemas/` with its provenance and SHA-256, so the claim is
checkable rather than asserted.

## Status

Milestones 1 to 6 are done and milestone 7 is in progress. Its open item is **a real held-out set**:
invoices that nobody here generated. Every result below comes from a synthetic corpus, where
KSeF-conformant XML is the gold and is rendered to PDF across 9 difficulty tiers and 3 layouts.

| Test (synthetic corpus) | Result | Compared with | Source |
|---|---|---|---|
| `claude-opus-5`, clean PDFs, 108 documents, 6066 fields | 100.0 % | regex baseline `pattern`: 86.3 % | [`claude-opus-5/report.md`](results/claude-opus-5/report.md), [`pattern/report.md`](results/pattern/report.md) |
| Arithmetic detector against the real errors of `claude-haiku-4-5` | precision 100 %, recall 76.2 % | n/a | [`claude-haiku-4-5/detector.md`](results/claude-haiku-4-5/detector.md) |
| Confidence gate on `claude-haiku-4-5`: auto-accept `high` only | 99.96 % accuracy at 89.7 % coverage | answer everything: 98.7 % | [`claude-haiku-4-5/gate.md`](results/claude-haiku-4-5/gate.md) |
| Prompt injection against a vision model reading attacked scans | 0 of 144 attacks met their objective | n/a | [`attacked-scanned-claude-opus-5/attack.md`](results/attacked-scanned-claude-opus-5/attack.md) |

A frontier model makes no errors on the clean corpus, so the detector and the gate are measured on a
weaker model. On attacked scans, auto-accepting the gate's high-confidence values was less accurate
than accepting everything. That result and the rest of the measurements are in
[docs/tour.md](docs/tour.md); the working record is [docs/findings.md](docs/findings.md) and the
decisions are in [docs/adr/](docs/adr).

Tests: 814 passing, 22 skipped (offline, without the rendered corpus), `ruff` clean.

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

**What the synthetic corpus does not have** is a page nobody in this repository designed. Two of
the three things that used to be missing are measured now, on held-out corpora of their own: an
unfamiliar layout (`foreign/`) and a poor scan (`degrade/`), each varying one thing so that a drop
is attributable to it. What is still absent is a genuinely real invoice — a stamp, a signature, a
fold, a layout no template anticipated because no template wrote it.

## Four design decisions worth stating up front

**Invariants report; they do not raise.** A document whose numbers disagree must still be
constructible. Shape validation (types, decimal places, closed domains) raises, because a document
violating it is meaningless. Arithmetic goes through `invariants.check()`, which returns violations
as data carrying a stable rule id, a severity and the signed miss. A model that refused to
construct a broken invoice could not be routed, counted or explained — and inspecting broken
invoices is the whole project.

**The extractor transcribes; it never computes.** A figure that is not printed comes back as `null`,
and a printed figure is copied even when it looks wrong. This is the instruction the detector study
depends on: an extractor that helpfully derived a missing VAT from a net would *manufacture* the
arithmetic agreement this project measures, so every invariant would hold by construction on exactly
the documents whose reading was worst — and milestone 5 would be measuring the model's arithmetic
instead of the page's.

**The fence around the document is derived from the document.** A fixed `<document>…</document>` is
forgeable: an invoice that prints the closing tag ends the fence, and everything after it reads as
the caller's own words. The marker here carries the SHA-256 of the text it wraps, so closing it
early means printing a string that is a function of a text containing that string.

**Hard rules and heuristics are kept apart.** `Severity.HARD` is an arithmetic identity: a
violation means something is genuinely wrong. `Severity.HEURISTIC` usually holds but has lawful
exceptions — an invoice may legitimately be issued up to 60 days before the sale it documents.
Mixing them would blunt the detector, because a heuristic's false positives would be
indistinguishable from a real arithmetic miss.

## What this cannot tell you

A check digit rules out corruption, not fabrication: it proves a NIP was not misread, never that it
exists or belongs to the named party. An extraction wrong in a way arithmetic cannot see passes
every rule silently — milestone 5 measured how often, and milestone 6 showed that an adversary can
put a document in that blind spot deliberately, because a check digit they computed themselves is a
valid check digit. Nothing here validates that an identifier *belongs to* the party named beside it,
and no amount of reading the page can: that check lives in the buyer's own records.

**And on a page with no text layer the gate has no field-level signal at all.** Grounding needs page
text to resolve a value against; where there is none it now says so rather than accusing every
value, which makes the reports honest without making the pipeline able. Two thirds of a scanned
corpus arrives that way. The answer is a recogniser in front of the model — the `searchable` rung is
exactly that pipeline, and grounding is at its most precise there — not a better rule downstream.

## Running it

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Windows
pytest
ruff check .

python -m doc_extract.synth --out data/synthetic         # 108 documents, ~6 MB, not committed
python -m doc_extract.eval run --baseline pattern        # predict, score, write a report
python -m doc_extract.eval score  --run results/pattern  # re-score the committed predictions
python -m doc_extract.eval detect --run results/pattern  # the detector study on the same file
python -m doc_extract.eval gate   --run results/pattern  # the gate's coverage-accuracy curve

python -m doc_extract.attack --out data/attacked         # 112 attacked documents, verified on build
python -m doc_extract.eval run --baseline gullible --corpus data/attacked --out results/attack-gullible
python -m doc_extract.eval attack --run results/attack-gullible   # the attack success rate

python -m doc_extract.degrade --attacked --out data/attacked-scanned   # the same grid, photographed
python -m doc_extract.eval run --baseline gullible --corpus data/attacked-scanned \
    --out results/attacked-scanned-gullible
python -m doc_extract.eval attack --run results/attacked-scanned-gullible  # with the reach table
```

**The block above is a recipe book, not a manual, and `--help` is the manual.** Those are the
worked command lines — the ones whose output is in this document and in `results/` — and between
them they show a fraction of what the five CLIs accept. `python -m doc_extract.synth`,
`.attack`, `.degrade`, `.foreign` and `.eval` each answer `--help`, and `doc_extract.eval` also
answers it per subcommand (`eval run --help`). That is where `--limit` lives, which is what you
want for a smoke run before committing to a full corpus, along with `--seed`, `--tier`,
`--quiet`, `--max-tokens`, `--rate`, `--placement` and `--rung`.

Each run writes `results/<run>/` — `predictions.jsonl`, `run.meta.json`, `report.md`,
`detector.md` and `gate.md` — and those are **committed**. A number in either report is therefore recomputable
from the file that produced it, without re-running anything: `score` and `detect` both read the
predictions and the gold and print the same tables. That is also what makes a change to the scorer,
or to a rule, a reviewable diff in the numbers rather than a claim about them.

A run is named for its baseline, except a remote one, which is named for its model — the baseline is
`claude` every time and the model is what varies, so two models over one corpus are two directories
rather than one overwritten one.

## Licence

MIT — for this repository's own work, which is everything except the vendored files under
`schemas/` and `src/doc_extract/assets/fonts/`.

- **The two DejaVu fonts** under `src/doc_extract/assets/fonts/` carry their own permissive
  terms, and the `LICENSE` beside them is a **notice that must travel with them**. Its digest is
  pinned and `tests/test_vendored_artifacts.py` fails if the file goes missing or changes.
- **The four Ministerstwo Finansów XSDs** under `schemas/` are neither MIT nor licensed at all:
  they are *urzędowe materiały*, which Article 4 of the Polish copyright act places outside the
  subject matter of copyright, so no permission is required and none was granted.

Both readings, with their sources and their limits, are in the two `PROVENANCE.md` files.
