# the gate — noisy

| | |
|---|---|
| run | `results/noisy` |
| answered by | `noisy` |
| saw | the gold |
| values asserted | 6630 |
| of which wrong | 105 |
| assessed below | 5849 |
| of those, wrong | 105 |
| asserted but not assessable | 781 (wrong: 0) |
| asserted on a page with no text | 0 |
| gold values never asserted | 44 |
| documents with no invoice | 0 |

## The three signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work. `contention` is the one whose precision is bounded by construction: when two of a reading's values claim one printed figure it flags **both**, because no label-free fact says which of the two is the intruder, so about half of what it flags is the correct sibling of a wrong value.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 77 | 0 | 28 | 5744 | 100 % | 73.3 % |
| `arithmetic` | 83 | 2086 | 22 | 3658 | 3.8 % | 79.0 % |
| `contention` | 0 | 0 | 105 | 5744 | — | 0.0 % |
| `any of the three` | 93 | 2086 | 12 | 3658 | 4.3 % | 88.6 % |

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
* 781 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 0 of them are wrong, and nothing in the tables above counts those.
* The confidence levels are produced by fixed rules over the three signals, not by weights fitted to this corpus. That is why there are four and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
