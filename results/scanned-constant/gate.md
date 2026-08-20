# the gate — constant

| | |
|---|---|
| run | `results/scanned-constant` |
| answered by | `constant` |
| saw | nothing |
| values asserted | 216 |
| of which wrong | 184 |
| gold values never asserted | 5310 |
| asserted but not assessable | 716 |
| asserted on a page with no text | 432 |
| documents with no invoice | 0 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 96 | 0 | 88 | 32 | 100 % | 52.2 % |
| `arithmetic` | 0 | 0 | 184 | 32 | — | 0.0 % |
| `either` | 96 | 0 | 88 | 32 | 100 % | 52.2 % |

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
* 716 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. They are values a model can get wrong, and nothing above measures whether it did.
* **432 of the 648 asserted value(s) (66.7 %) sit on a page with no text layer at all, and are outside the curve.** Grounding resolves a value against page text and there is none, so it answers `NO_TEXT` — *I could not ask* — rather than `UNGROUNDED`, which would have claimed the value is missing from the page. They are routed `review` and carry no confidence, so every figure above is over the 216 value(s) this pipeline could actually assess. **The gate has no signal at all on the rest**, and that is a statement about the page rather than about the reader: a recogniser in front of the model brings the signal back.
* **`arithmetic` flagged nothing at all**, while 184 asserted value(s) were wrong. No identity was broken: a prediction can be internally consistent and still be wrong everywhere, which is what a constant or a wholly-invented answer looks like from the arithmetic's side.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
