# the gate — gullible

| | |
|---|---|
| run | `results/attacked-scanned-gullible` |
| answered by | `gullible` |
| saw | the page and the gold |
| values asserted | 9894 |
| of which wrong | 66 |
| assessed below | 2697 |
| of those, wrong | 66 |
| asserted but not assessable | 1149 (wrong: 0) |
| asserted on a page with no text | 6048 (wrong: 0) |
| gold values never asserted | 0 |
| documents with no invoice | 6 |

## The three signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work. `contention` is the one that accuses a **pair**: when two of a reading's values claim one printed figure it flags both, because no label-free fact says which of the two is the intruder. Where the sibling is a correct reading that caps its precision near a half; where both belong to a row the page never printed, nothing it flags is correct and the row below says which of the two this run is.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 6 | 0 | 60 | 2631 | 100 % | 9.1 % |
| `arithmetic` | 48 | 889 | 18 | 1742 | 5.1 % | 72.7 % |
| `contention` | 12 | 0 | 54 | 2631 | 100 % | 18.2 % |
| `any of the three` | 48 | 889 | 18 | 1742 | 5.1 % | 72.7 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 65.3 % | 99.0 % | 1760 | 18 |
| `medium` | `review` | 99.8 % | 97.8 % | 2691 | 60 |
| `low` | `review` | 100 % | 97.6 % | 2697 | 66 |
| `none` | `reject` | 100 % | 97.6 % | 2697 | 66 |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 0 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 1149 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 0 of them are wrong, and nothing in the tables above counts those.
* 6 document(s) produced no invoice, so none of their fields was assessed. The pipeline had already refused them.
* **6048 of the 9894 asserted value(s) (61.1 %) sit on a page with no text layer at all, and are outside the curve.** Grounding resolves a value against page text and there is none, so it answers `NO_TEXT` — *I could not ask* — rather than `UNGROUNDED`, which would have claimed the value is missing from the page. They are routed `review` and carry no confidence, so every figure above is over the 2697 value(s) this pipeline could actually assess, and 0 wrong value(s) sit in the excluded set where nothing measures them. **The gate has no signal at all on those**, and that is a statement about the page rather than about the reader: a recogniser in front of the model brings the signal back.
* **Against the ungated policy.** Accepting every asserted value — the 2697 below plus the 7197 excluded from them — is 99.3 % accurate. The `high` row is 99.0 %, so on this corpus auto-accepting the gate's confident bucket is **still less accurate than not gating at all**, because its signal exists only where the page kept text and the excluded values are largely right. The `none` row is *not* that comparison: it accepts everything the gate could assess, which is a different set.
* **`grounding` missed 60 of the 66 wrong asserted value(s)** and flagged 6 of them. It asks whether a value is *on the page*, not whether it is in the *right place*: a reader that lifts a real figure out of the wrong column is fully grounded and completely wrong, and one that borrows a word from the other party's address is too. A **text** value is now resolved to one place rather than to whichever occurrence of each word came first, which is what makes its recorded spans a location at all; an amount or an identifier still resolves to every occurrence of itself. `contention` uses those places to catch the one wrong-column shape that is decidable without knowing which column is which — two values claiming one figure — and `docs/adr/0002_placement.md` carries the two shapes that leaves standing.
* `contention` flagged 12 asserted value(s), and **every one of them was already named by a hard rule**, so the gate reached the same verdict without it and what this signal adds here is the attribution, not the routing. It names the two fields that share a printed figure, where an arithmetic violation names the whole `lines` collection; the two catch overlapping populations and only the narrower one says *which* values are involved.
* The confidence levels are produced by fixed rules over the three signals, not by weights fitted to this corpus. That is why there are four and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
