# the gate — pattern

| | |
|---|---|
| run | `results/foreign-pattern` |
| answered by | `pattern` |
| saw | the page |
| values asserted | 0 |
| of which wrong | 0 |
| assessed below | 0 |
| of those, wrong | 0 |
| asserted but not assessable | 0 |
| asserted on a page with no text | 0 |
| gold values never asserted | 0 |
| documents with no invoice | 108 |

## The three signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work. `contention` is the one that accuses a **pair**: when two of a reading's values claim one printed figure it flags both, because no label-free fact says which of the two is the intruder. Where the sibling is a correct reading that caps its precision near a half; where both belong to a row the page never printed, nothing it flags is correct and the row below says which of the two this run is.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 0 | 0 | 0 | 0 | — | — |
| `arithmetic` | 0 | 0 | 0 | 0 | — | — |
| `contention` | 0 | 0 | 0 | 0 | — | — |
| `any of the three` | 0 | 0 | 0 | 0 | — | — |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | — | — | 0 | 0 |
| `medium` | `review` | — | — | 0 | 0 |
| `low` | `review` | — | — | 0 | 0 |
| `none` | `reject` | — | — | 0 | 0 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 0 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 108 document(s) produced no invoice, so none of their fields was assessed. The pipeline had already refused them.
* **Nothing asserted was wrong**, so the gate had nothing to catch. Accuracy is 100 % at every level and the curve is flat by construction; it says the gate does not block correct work, and nothing about whether it blocks incorrect work.
* The confidence levels are produced by fixed rules over the three signals, not by weights fitted to this corpus. That is why there are four and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
