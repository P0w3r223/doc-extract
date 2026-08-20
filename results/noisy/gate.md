# the gate — noisy

| | |
|---|---|
| run | `results/noisy` |
| answered by | `noisy` |
| saw | the gold |
| values asserted | 5849 |
| of which wrong | 105 |
| gold values never asserted | 44 |
| asserted but not assessable | 781 |
| documents with no invoice | 0 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 77 | 0 | 28 | 5744 | 100 % | 73.3 % |
| `arithmetic` | 83 | 2086 | 22 | 3658 | 3.8 % | 79.0 % |
| `either` | 93 | 2086 | 12 | 3658 | 4.3 % | 88.6 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 62.7 % | 99.7 % | 3670 | 12 |
| `medium` | `review` | 98.7 % | 99.5 % | 5772 | 28 |
| `low` | `review` | 98.7 % | 99.5 % | 5772 | 28 |
| `none` | `reject` | 100 % | 98.2 % | 5849 | 105 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 44 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 781 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. They are values a model can get wrong, and nothing above measures whether it did.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
