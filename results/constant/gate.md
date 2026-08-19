# the gate — constant

| | |
|---|---|
| run | `results/constant` |
| answered by | `constant` |
| saw | nothing |
| values asserted | 648 |
| of which wrong | 552 |
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
* **`arithmetic` flagged nothing at all**, while 552 asserted value(s) were wrong. For grounding that has one cause worth naming: it asks whether a value is *on the page*, not whether it is in the *right place*. A reader that lifts a real figure out of the wrong column is fully grounded and completely wrong. The spans are recorded, so a geometric check could ask the second question — it is not built.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
