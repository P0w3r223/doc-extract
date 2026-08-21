# the gate — constant

| | |
|---|---|
| run | `results/scanned-constant` |
| answered by | `constant` |
| saw | nothing |
| values asserted | 1364 |
| of which wrong | 576 |
| assessed below | 216 |
| of those, wrong | 184 |
| asserted but not assessable | 716 (wrong: 24) |
| asserted on a page with no text | 432 (wrong: 368) |
| gold values never asserted | 5310 |
| documents with no invoice | 0 |

## The three signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work. `contention` is the one that accuses a **pair**: when two of a reading's values claim one printed figure it flags both, because no label-free fact says which of the two is the intruder. Where the sibling is a correct reading that caps its precision near a half; where both belong to a row the page never printed, nothing it flags is correct and the row below says which of the two this run is.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 96 | 0 | 88 | 32 | 100 % | 52.2 % |
| `arithmetic` | 0 | 0 | 184 | 32 | — | 0.0 % |
| `contention` | 0 | 0 | 184 | 32 | — | 0.0 % |
| `any of the three` | 96 | 0 | 88 | 32 | 100 % | 52.2 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 55.6 % | 26.7 % | 120 | 88 |
| `medium` | `review` | 55.6 % | 26.7 % | 120 | 88 |
| `low` | `review` | 55.6 % | 26.7 % | 120 | 88 |
| `none` | `reject` | 100 % | 14.8 % | 216 | 184 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 5310 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 716 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 24 of them are wrong, and nothing in the tables above counts those.
* **432 of the 1364 asserted value(s) (31.7 %) sit on a page with no text layer at all, and are outside the curve.** Grounding resolves a value against page text and there is none, so it answers `NO_TEXT` — *I could not ask* — rather than `UNGROUNDED`, which would have claimed the value is missing from the page. They are routed `review` and carry no confidence, so every figure above is over the 216 value(s) this pipeline could actually assess, and 368 wrong value(s) sit in the excluded set where nothing measures them. **The gate has no signal at all on those**, and that is a statement about the page rather than about the reader: a recogniser in front of the model brings the signal back.
* **Against the ungated policy.** Accepting every asserted value — the 216 below plus the 1148 excluded from them — is 57.8 % accurate. The `high` row is 26.7 %, so on this corpus auto-accepting the gate's confident bucket is **still less accurate than not gating at all**, because its signal exists only where the page kept text and the excluded values are largely right. The `none` row is *not* that comparison: it accepts everything the gate could assess, which is a different set.
* **`arithmetic` flagged nothing at all**, while 184 asserted value(s) were wrong. No identity was broken: a prediction can be internally consistent and still be wrong everywhere, which is what a constant or a wholly-invented answer looks like from the arithmetic's side.
* The confidence levels are produced by fixed rules over the three signals, not by weights fitted to this corpus. That is why there are four and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
