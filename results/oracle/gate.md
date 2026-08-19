# the gate — oracle

| | |
|---|---|
| run | `results/oracle` |
| answered by | `oracle` |
| saw | the gold |
| values asserted | 5892 |
| of which wrong | 0 |
| gold values never asserted | 0 |
| documents with no invoice | 0 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 0 | 0 | 0 | 5892 | — | — |
| `arithmetic` | 0 | 0 | 0 | 5892 | — | — |
| `either` | 0 | 0 | 0 | 5892 | — | — |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 100 % | 100 % | 5892 | 0 |
| `medium` | `review` | 100 % | 100 % | 5892 | 0 |
| `low` | `review` | 100 % | 100 % | 5892 | 0 |
| `none` | `reject` | 100 % | 100 % | 5892 | 0 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 0 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* **Nothing asserted was wrong**, so the gate had nothing to catch. Accuracy is 100 % at every level and the curve is flat by construction; it says the gate does not block correct work, and nothing about whether it blocks incorrect work.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
