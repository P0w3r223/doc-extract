# Where a grounded value sits, and why the geometric check is still not built

Date: 2026-08-21
Status: accepted
Author: P0w3r223 + Claude
Related to: milestone 5 (`src/doc_extract/ground/`), milestone 7 (`src/doc_extract/ground/place.py`),
`results/*/gate.md`

---

## Context

Milestone 5 built `ground/` as the complement to the arithmetic detector: the arithmetic catches
every wrong number and no wrong *name*, because a name has no redundancy behind it, so the other
half of the question is whether a value can be found on the page at all. It works — 100 % precision
at the field level, and on the one rung of a scanned corpus that keeps a text layer it is the most
precise measurement in this project, no false alarm on 1902 asserted values.

It also has a documented blind spot, and the blind spot has a name and a population. `eval/pattern.py`
is a regex reader that lifts real figures out of the wrong column: on M4's corpus it asserts 292
values that disagree with the gold, and grounding flags **none** of them. Every one is a real string
that the page really prints — just not where that field is printed. The project has recorded the
intended answer since M5:

> Grounding asks whether a value is on the page, not whether it is in the right place. … The spans
> are recorded, so a geometric check could ask the second question. It is not built.

This ADR records what happened when it was built, because the first clause turned out to be false.

## The finding: the spans did not record a place

`Grounding.spans` was assembled two different ways and neither was a location.

**A text value was tallied, not located.** `find_words` walked the value's words and popped, for
each, the first occurrence of that word anywhere on the page. So `clean-0001` — whose buyer is
`Przychodnia Rodzinna VITAMED sp. z o.o.`, printed complete in one cell — grounded `Przychodnia`,
`Rodzinna` and `VITAMED` against the buyer's cell and then grounded `sp.`, `z` and `o.o.` against
the **seller's** legal form 142 points up the page. Fully grounded, and half the evidence belonged
to a different company. That is the same failure `resolve`'s own docstring warns about for exemption
codes — *grounding for a reason that has nothing to do with the field being right* — and it was
general rather than confined to rates.

**A value match returned every occurrence.** `find_value` returns the spans covering the winning
candidate wherever it occurs, so an amount printed in its row and again in the rate totals grounds
to both. On gold, values came back with 4, 6, 8, 10 and in one case 14 spans.

The consequence is that a geometric rule reading those spans is reading a bag of occurrences.
Measured, on gold — a reading with nothing wrong in it anywhere, and the control that has caught
every previous defect in this layer:

| candidate rule | fires on gold |
|---|---:|
| the value's spans span more than one column | 1462 / 5892 (24.8 %) |
| the value's spans sit more than one row apart | 1923 / 5892 (32.6 %) |
| a text value leaves words unclaimed in its cell | 934 / 5892 (15.9 %) |

A signal whose false-alarm rate on a perfect reading is a quarter of the corpus is not a signal.
None of these is a bad idea about invoices; all of them were being asked of the wrong data.

## Decision

**1. A text value is located.** `ground/place.py` requires the whole value to be found in one place
— a cell, plus the cells a wrapped line continues into, in the same column and a neighbouring row.
The spans that come back are that place.

**2. The place's two bounds are measured, not assumed.** Anchoring to a single cell fails the
control on 52.1 % of gold text values, because the renderer breaks a long description across lines
and `source/layout.py` makes each line its own cell — so the column continuation is necessary, not
decorative. Of the two bounds it is the **column** that discriminates: removing it takes the catch
on `pattern` from 19 wrong descriptions to none, while every vertical reach from 0.5 to 20× the
shipped one gives the identical control and the identical catch. `WRAP_REACH` is therefore a bound
that admits wrapping, not a threshold tuned between two populations, and the module says so.

**3. The value path keeps every occurrence.** Narrowing it needs a criterion for which occurrence is
the right one, and for an isolated amount there is no label-free one — knowing that a net belongs in
the net column is exactly the knowledge `ground/` is not allowed to have (the same rule that keeps
`synth/render.py`'s labels out of `extract/prompt.py`). A *joint* criterion exists in principle —
choose the occurrence consistent with the row and column its siblings chose — and it is not built;
see below.

**4. The geometric check is still not built, and now for a stated reason.** Placement is a
precondition for it, not an implementation of it.

## What the fix bought, and what it did not

Placement was imposed at no cost to any correct reading. Text values that ground today and still
ground after it, on four populations:

| population | correct values kept | wrong values newly caught |
|---|---:|---:|
| gold (the control) | 1238 / 1238 | — |
| `claude-opus-5` (a perfect reading) | 1238 / 1238 | — |
| `claude-haiku-4-5` | 1186 / 1186 | 1 / 3 |
| `pattern` | 752 / 752 | 19 / 181 |

So the mechanism is repaired and the blindness is barely dented: 19 of `pattern`'s 292. **The reason
is worth recording, because it is not the one that was expected.** The dominant failure is a
description that stops early, and the natural check — did the value claim the whole cell it sat in?
— cannot see it. Measured: **100 %** of `pattern`'s wrong descriptions claim their entire cell. They
are not truncations *within* a cell. The renderer wraps a description across lines, each line is its
own cell, and the reader took one whole cell of a two-cell run. Asking the question of the whole
column region instead fails the control in the other direction — only 8.9 % of gold values claim
their region, because the region also holds the neighbouring field.

So a completeness check needs to distinguish *the rest of my wrapped value* from *the next field
down this column*, and neither the cell nor the column decides it. The page does: in a table, a
continuation line carries only the wrapping column while a new row carries all of them. That is a
label-free structural signal and it is a different piece of work, with its own control to clear.

## Consequences

- **`gate.md` is the affected committed artifact, and all 22 were regenerated.** So is `attack.md`'s
  **leak** column, which routes through `decide.confidence` and therefore through grounding; all 7
  were regenerated and none moved, because the documents involved were already routed `review` on
  some other field. That is an observation about this run and not an invariant, and neither figure
  can be pulled into `tests/test_results_committed.py`'s equality check for the same reason: both
  need the rendered pages, which the check exists to avoid needing. They are the two numbers in this
  repository that can drift in silence, which is why regenerating them is part of a change to this
  layer rather than a follow-up to it.
- Grounding raised no new false positives anywhere, and its recall improves slightly. It is still
  not a detector of values read out of the wrong column, and the headline tables continue to say so.
- **`decide/`'s rules and `eval/selective.py` are unchanged** — only a figure in a docstring moved.
  Placement changes what `coverage` measures, not what the levels mean, and a value that loses
  coverage lands in `PARTIAL` → `LOW` → `review` by the rules that were already there.
- The two things this leaves open are now specific rather than aspirational: a **continuation-aware
  completeness check**, which the measurement above scopes; and a **joint placement** across a
  reading's field instances, which is what would let the value path choose an occurrence and would
  answer the wrong-column question directly. Both need a control that clears gold, and the naive
  version of each has now been measured failing one.

## Addendum, 2026-08-21: the foreign arm supplies the population (M7i)

Two paid arms over `data/foreign` turned the wrong-column question from a property of a regex
baseline into a property of a **real model's errors**, and added one blind spot nobody predicted.

**The population.** `claude-haiku-4-5` reads the foreign corpus at 97.2 % against 98.6 % on its own
page (matched over the 107 documents both runs answered — the raw 97.8 %/98.1 % pair is confounded
by one own-page `max_tokens` failure). The 1.4-point cost is not the point; the **shape** is. Its
errors become *right value, wrong field* in two independent forms:

- **58 spurious `lines[].discount`**, of which **53 are exactly that row's own `net`**, 3 its `vat`,
  2 nothing. The same failure exists on the own page — 11 spurious discounts, 9 of them the row's
  net — so the foreign corpus **amplifies it about fivefold rather than creating it**. All 58 are on
  the two layouts that print an item table; the third prints its positions as running text and has
  no column to shift into, so it is not a control and nothing here isolates *why* a table invites
  the net into an empty discount cell.
- **23 wrong dates**, all on that third layout, 19 of them exactly the other date printed on the
  same invoice.

Grounding's recall against the whole population is **34.8 %**, against 85.7 % on the same model's
own-page errors, with precision **100 %** on both. A value one column over is on the page, in the
right row; the other date is on the page, in the right block. Both are textually indistinguishable
from a correct reading and geometrically distinguishable from one.

That is what makes joint placement worth building rather than merely coherent: a `discount` whose
only occurrence sits inside the net column, while every sibling of its row sits in its own, is
detectable from the spans `place.py` now records — and this is the first population where doing so
would catch a real model rather than a regex. **47 of the 58 spurious discounts resolve to exactly
one span on the page**, so joint placement would have an unambiguous location for 81 % of them; the
remaining 11 would need the weaker "no occurrence in the discount column" formulation.

**And a second, narrower defect the arm found rather than confirmed.** `resolve._source_boundary`
rejects a hit that continues into a longer run of alphanumerics *on the page*. The identifier
projection has already stripped the separators, so when a page groups an identifier — every foreign
dialect prints an IBAN in groups of six via the shared `foreign/render.py::_iban`, e.g. `PL 049911
602207 394837 519847 27` — a prefix ending on a **grouping boundary** has a space after it in the
source and passes the check. haiku dropped a trailing group on 5 accounts and all 5 grounded. **The
determinant is the boundary, not the layout**: an account truncated *mid*-group on another dialect
was correctly `UNGROUNDED`. The rule is not wrong; it is asking about the page while the value it
compares has been normalised past the thing that would have answered.

**Nothing leaked, and the reason is the design.** All 11 wrong accounts fail mod-97 and the
check-digit rule flags all 11 — 6 route `reject`, 5 `review`, **0 `accept`**. Grounding's silence
cost nothing because the arithmetic covers exactly what it missed. Fixing the boundary rule (compare
against a projection that remembers where the separators were) is worth doing and is **not urgent**:
it would move values from `review` to `reject`, not from `accept` to caught.
