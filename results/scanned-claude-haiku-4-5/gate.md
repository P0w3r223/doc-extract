# the gate — claude-haiku-4-5

| | |
|---|---|
| run | `results/scanned-claude-haiku-4-5` |
| answered by | `claude-haiku-4-5` |
| saw | the page |
| values asserted | 1903 |
| of which wrong | 145 |
| gold values never asserted | 41 |
| asserted but not assessable | 759 |
| asserted on a page with no text | 3792 |
| documents with no invoice | 1 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 136 | 0 | 9 | 1758 | 100 % | 93.8 % |
| `arithmetic` | 23 | 30 | 122 | 1728 | 43.4 % | 15.9 % |
| `either` | 136 | 30 | 9 | 1728 | 81.9 % | 93.8 % |

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
* 759 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. They are values a model can get wrong, and nothing above measures whether it did.
* 1 document(s) produced no invoice, so none of their fields was assessed. The pipeline had already refused them.
* **3792 of the 5695 asserted value(s) (66.6 %) sit on a page with no text layer at all, and are outside the curve.** Grounding resolves a value against page text and there is none, so it answers `NO_TEXT` — *I could not ask* — rather than `UNGROUNDED`, which would have claimed the value is missing from the page. They are routed `review` and carry no confidence, so every figure above is over the 1903 value(s) this pipeline could actually assess. **The gate has no signal at all on the rest**, and that is a statement about the page rather than about the reader: a recogniser in front of the model brings the signal back.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
