# the gate — pattern

| | |
|---|---|
| run | `results/pattern` |
| answered by | `pattern` |
| saw | the page |
| values asserted | 6115 |
| of which wrong | 292 |
| assessed below | 5356 |
| of those, wrong | 292 |
| asserted but not assessable | 759 (wrong: 0) |
| asserted on a page with no text | 0 |
| gold values never asserted | 323 |
| documents with no invoice | 4 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 19 | 0 | 273 | 5064 | 100 % | 6.5 % |
| `arithmetic` | 238 | 1424 | 54 | 3640 | 14.3 % | 81.5 % |
| `either` | 238 | 1424 | 54 | 3640 | 14.3 % | 81.5 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 69.0 % | 98.5 % | 3694 | 54 |
| `medium` | `review` | 99.6 % | 94.9 % | 5337 | 273 |
| `low` | `review` | 100 % | 94.5 % | 5356 | 292 |
| `none` | `reject` | 100 % | 94.5 % | 5356 | 292 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 323 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 759 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 0 of them are wrong, and nothing in the tables above counts those.
* 4 document(s) produced no invoice, so none of their fields was assessed. The pipeline had already refused them.
* **`grounding` missed 273 of the 292 wrong asserted value(s)** and flagged 19 of them. It asks whether a value is *on the page*, not whether it is in the *right place*: a reader that lifts a real figure out of the wrong column is fully grounded and completely wrong, and one that borrows a word from the other party's address is too. A value is now resolved to **one place** rather than to whichever occurrence of each word came first, which is what makes the recorded spans a location at all — but the geometric check that would use them is still not built, and `docs/adr/0002_placement.md` carries what it turned out to need.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
