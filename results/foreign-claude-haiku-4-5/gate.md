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

## The three signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work. `contention` is the one that accuses a **pair**: when two of a reading's values claim one printed figure it flags both, because no label-free fact says which of the two is the intruder. Where the sibling is a correct reading that caps its precision near a half; where both belong to a row the page never printed, nothing it flags is correct and the row below says which of the two this run is.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 49 | 0 | 92 | 5779 | 100 % | 34.8 % |
| `arithmetic` | 58 | 957 | 83 | 4822 | 5.7 % | 41.1 % |
| `contention` | 25 | 30 | 116 | 5749 | 45.5 % | 17.7 % |
| `any of the three` | 89 | 963 | 52 | 4816 | 8.5 % | 63.1 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 82.2 % | 98.9 % | 4868 | 52 |
| `medium` | `review` | 99.2 % | 98.4 % | 5871 | 92 |
| `low` | `review` | 99.8 % | 97.8 % | 5910 | 131 |
| `none` | `reject` | 100 % | 97.6 % | 5920 | 141 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 30 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 724 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 0 of them are wrong, and nothing in the tables above counts those.
* **`grounding` missed 92 of the 141 wrong asserted value(s)** and flagged 49 of them. It asks whether a value is *on the page*, not whether it is in the *right place*: a reader that lifts a real figure out of the wrong column is fully grounded and completely wrong, and one that borrows a word from the other party's address is too. A **text** value is now resolved to one place rather than to whichever occurrence of each word came first, which is what makes its recorded spans a location at all; an amount or an identifier still resolves to every occurrence of itself. `contention` uses those places to catch the one wrong-column shape that is decidable without knowing which column is which — two values claiming one figure — and `docs/adr/0002_placement.md` carries the two shapes that leaves standing.
* `contention` flagged 55 asserted value(s), and 7 of them (1 wrong) carried **no** arithmetic accusation, so the gate would not have demoted them otherwise. It names the two fields that share a printed figure, where an arithmetic violation names the whole `lines` collection; the two catch overlapping populations and only the narrower one says *which* values are involved.
* The confidence levels are produced by fixed rules over the three signals, not by weights fitted to this corpus. That is why there are four and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
