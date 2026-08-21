# the gate — claude-haiku-4-5

| | |
|---|---|
| run | `results/foreign-claude-haiku-4-5` |
| answered by | `claude-haiku-4-5` |
| saw | the page |
| values asserted | 6644 |
| of which wrong | 141 |
| assessed below | 5920 |
| of those, wrong | 141 |
| asserted but not assessable | 724 (wrong: 0) |
| asserted on a page with no text | 0 |
| gold values never asserted | 30 |
| documents with no invoice | 0 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 49 | 0 | 92 | 5779 | 100 % | 34.8 % |
| `arithmetic` | 58 | 957 | 83 | 4822 | 5.7 % | 41.1 % |
| `either` | 88 | 957 | 53 | 4822 | 8.4 % | 62.4 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 82.3 % | 98.9 % | 4875 | 53 |
| `medium` | `review` | 99.2 % | 98.4 % | 5871 | 92 |
| `low` | `review` | 99.8 % | 97.8 % | 5910 | 131 |
| `none` | `reject` | 100 % | 97.6 % | 5920 | 141 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 30 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 724 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 0 of them are wrong, and nothing in the tables above counts those.
* **`grounding` missed 92 of the 141 wrong asserted value(s)** and flagged 49 of them. It asks whether a value is *on the page*, not whether it is in the *right place*: a reader that lifts a real figure out of the wrong column is fully grounded and completely wrong, and one that borrows a word from the other party's address is too. A **text** value is now resolved to one place rather than to whichever occurrence of each word came first, which is what makes its recorded spans a location at all; an amount or an identifier still resolves to every occurrence of itself. The geometric check that would use either is not built, and `docs/adr/0002_placement.md` carries what it turned out to need.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
