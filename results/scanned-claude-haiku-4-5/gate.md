# the gate — claude-haiku-4-5

| | |
|---|---|
| run | `results/scanned-claude-haiku-4-5` |
| answered by | `claude-haiku-4-5` |
| saw | the page |
| values asserted | 6454 |
| of which wrong | 485 |
| assessed below | 1903 |
| of those, wrong | 145 |
| asserted but not assessable | 759 (wrong: 33) |
| asserted on a page with no text | 3792 (wrong: 307) |
| gold values never asserted | 41 |
| documents with no invoice | 1 |

## The three signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work. `contention` is the one that accuses a **pair**: when two of a reading's values claim one printed figure it flags both, because no label-free fact says which of the two is the intruder. Where the sibling is a correct reading that caps its precision near a half; where both belong to a row the page never printed, nothing it flags is correct and the row below says which of the two this run is.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 136 | 0 | 9 | 1758 | 100 % | 93.8 % |
| `arithmetic` | 23 | 30 | 122 | 1728 | 43.4 % | 15.9 % |
| `contention` | 0 | 0 | 145 | 1758 | — | 0.0 % |
| `any of the three` | 136 | 30 | 9 | 1728 | 81.9 % | 93.8 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 91.3 % | 99.5 % | 1737 | 9 |
| `medium` | `review` | 92.9 % | 99.5 % | 1767 | 9 |
| `low` | `review` | 99.1 % | 93.2 % | 1886 | 128 |
| `none` | `reject` | 100 % | 92.4 % | 1903 | 145 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 41 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 759 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 33 of them are wrong, and nothing in the tables above counts those.
* 1 document(s) produced no invoice, so none of their fields was assessed. The pipeline had already refused them.
* **3792 of the 6454 asserted value(s) (58.8 %) sit on a page with no text layer at all, and are outside the curve.** Grounding resolves a value against page text and there is none, so it answers `NO_TEXT` — *I could not ask* — rather than `UNGROUNDED`, which would have claimed the value is missing from the page. They are routed `review` and carry no confidence, so every figure above is over the 1903 value(s) this pipeline could actually assess, and 307 wrong value(s) sit in the excluded set where nothing measures them. **The gate has no signal at all on those**, and that is a statement about the page rather than about the reader: a recogniser in front of the model brings the signal back.
* **Against the ungated policy.** Accepting every asserted value — the 1903 below plus the 4551 excluded from them — is 92.5 % accurate. The `high` row is 99.5 %, so on this corpus auto-accepting the gate's confident bucket is **more accurate than not gating at all**, which is what a gate is for. The `none` row is *not* that comparison: it accepts everything the gate could assess, which is a different set.
* The confidence levels are produced by fixed rules over the three signals, not by weights fitted to this corpus. That is why there are four and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
