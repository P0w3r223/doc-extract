# the gate — claude-opus-5

| | |
|---|---|
| run | `results/scanned-claude-opus-5` |
| answered by | `claude-opus-5` |
| saw | the page |
| values asserted | 5892 |
| of which wrong | 1 |
| gold values never asserted | 0 |
| asserted but not assessable | 782 |
| documents with no invoice | 0 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 1 | 3989 | 0 | 1902 | 0.0 % | 100 % |
| `arithmetic` | 1 | 0 | 0 | 5891 | 100 % | 100 % |
| `either` | 1 | 3989 | 0 | 1902 | 0.0 % | 100 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 32.3 % | 100 % | 1902 | 0 |
| `medium` | `review` | 32.3 % | 100 % | 1902 | 0 |
| `low` | `review` | 32.3 % | 100 % | 1902 | 0 |
| `none` | `reject` | 100 % | 99.98 % | 5892 | 1 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 0 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 782 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. They are values a model can get wrong, and nothing above measures whether it did.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
