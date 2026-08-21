# the gate — claude-haiku-4-5

| | |
|---|---|
| run | `results/claude-haiku-4-5` |
| answered by | `claude-haiku-4-5` |
| saw | the page |
| values asserted | 6599 |
| of which wrong | 77 |
| assessed below | 5837 |
| of those, wrong | 77 |
| asserted but not assessable | 762 (wrong: 0) |
| asserted on a page with no text | 0 |
| gold values never asserted | 5 |
| documents with no invoice | 1 |

## The three signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work. `contention` is the one that accuses a **pair**: when two of a reading's values claim one printed figure it flags both, because no label-free fact says which of the two is the intruder. Where the sibling is a correct reading that caps its precision near a half; where both belong to a row the page never printed, nothing it flags is correct and the row below says which of the two this run is.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 66 | 0 | 11 | 5760 | 100 % | 85.7 % |
| `arithmetic` | 42 | 529 | 35 | 5231 | 7.4 % | 54.5 % |
| `contention` | 9 | 9 | 68 | 5751 | 50.0 % | 11.7 % |
| `any of the three` | 75 | 529 | 2 | 5231 | 12.4 % | 97.4 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 89.7 % | 99.96 % | 5233 | 2 |
| `medium` | `review` | 98.9 % | 99.8 % | 5771 | 11 |
| `low` | `review` | 99.5 % | 99.2 % | 5809 | 49 |
| `none` | `reject` | 100 % | 98.7 % | 5837 | 77 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 5 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 762 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 0 of them are wrong, and nothing in the tables above counts those.
* 1 document(s) produced no invoice, so none of their fields was assessed. The pipeline had already refused them.
* `contention` flagged 18 asserted value(s), and **every one of them was already named by a hard rule**, so the gate reached the same verdict without it and what this signal adds here is the attribution, not the routing. It names the two fields that share a printed figure, where an arithmetic violation names the whole `lines` collection; the two catch overlapping populations and only the narrower one says *which* values are involved.
* The confidence levels are produced by fixed rules over the three signals, not by weights fitted to this corpus. That is why there are four and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
