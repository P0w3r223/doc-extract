# the gate — pattern

| | |
|---|---|
| run | `results/attack-pattern` |
| answered by | `pattern` |
| saw | the page |
| values asserted | 6097 |
| of which wrong | 329 |
| gold values never asserted | 343 |
| asserted but not assessable | 812 |
| documents with no invoice | 0 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 0 | 0 | 329 | 5768 | — | 0.0 % |
| `arithmetic` | 252 | 1351 | 77 | 4417 | 15.7 % | 76.6 % |
| `either` | 252 | 1351 | 77 | 4417 | 15.7 % | 76.6 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 73.7 % | 98.3 % | 4494 | 77 |
| `medium` | `review` | 100 % | 94.6 % | 6097 | 329 |
| `low` | `review` | 100 % | 94.6 % | 6097 | 329 |
| `none` | `reject` | 100 % | 94.6 % | 6097 | 329 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 343 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 812 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. They are values a model can get wrong, and nothing above measures whether it did.
* **`grounding` flagged nothing at all**, while 329 asserted value(s) were wrong. It asks whether a value is *on the page*, not whether it is in the *right place*: a reader that lifts a real figure out of the wrong column is fully grounded and completely wrong, and one that borrows a word from the other party's address is too. The spans are recorded, so a geometric check could ask the second question — it is not built.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
