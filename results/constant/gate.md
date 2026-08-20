# the gate — constant

| | |
|---|---|
| run | `results/constant` |
| answered by | `constant` |
| saw | nothing |
| values asserted | 1364 |
| of which wrong | 576 |
| assessed below | 648 |
| of those, wrong | 552 |
| asserted but not assessable | 716 (wrong: 24) |
| asserted on a page with no text | 0 |
| gold values never asserted | 5310 |
| documents with no invoice | 0 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 324 | 0 | 228 | 96 | 100 % | 58.7 % |
| `arithmetic` | 0 | 0 | 552 | 96 | — | 0.0 % |
| `either` | 324 | 0 | 228 | 96 | 100 % | 58.7 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 50.0 % | 29.6 % | 324 | 228 |
| `medium` | `review` | 50.0 % | 29.6 % | 324 | 228 |
| `low` | `review` | 50.0 % | 29.6 % | 324 | 228 |
| `none` | `reject` | 100 % | 14.8 % | 648 | 552 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 5310 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 716 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 24 of them are wrong, and nothing in the tables above counts those.
* **`arithmetic` flagged nothing at all**, while 552 asserted value(s) were wrong. No identity was broken: a prediction can be internally consistent and still be wrong everywhere, which is what a constant or a wholly-invented answer looks like from the arithmetic's side.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
