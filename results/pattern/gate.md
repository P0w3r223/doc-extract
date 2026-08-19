# the gate — pattern

| | |
|---|---|
| run | `results/pattern` |
| answered by | `pattern` |
| saw | the page |
| values asserted | 5356 |
| of which wrong | 292 |
| gold values never asserted | 323 |
| documents with no invoice | 4 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 0 | 0 | 292 | 5064 | — | 0.0 % |
| `arithmetic` | 238 | 1424 | 54 | 3640 | 14.3 % | 81.5 % |
| `either` | 238 | 1424 | 54 | 3640 | 14.3 % | 81.5 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 69.0 % | 98.5 % | 3694 | 54 |
| `medium` | `review` | 100 % | 94.5 % | 5356 | 292 |
| `low` | `review` | 100 % | 94.5 % | 5356 | 292 |
| `none` | `reject` | 100 % | 94.5 % | 5356 | 292 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 323 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 4 document(s) produced no invoice, so none of their fields was assessed. The pipeline had already refused them.
* **`grounding` flagged nothing at all**, while 292 asserted value(s) were wrong. For grounding that has one cause worth naming: it asks whether a value is *on the page*, not whether it is in the *right place*. A reader that lifts a real figure out of the wrong column is fully grounded and completely wrong. The spans are recorded, so a geometric check could ask the second question — it is not built.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
