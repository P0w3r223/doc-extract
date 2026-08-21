# the gate — pattern

| | |
|---|---|
| run | `results/attack-pattern` |
| answered by | `pattern` |
| saw | the page |
| values asserted | 6911 |
| of which wrong | 331 |
| assessed below | 6099 |
| of those, wrong | 331 |
| asserted but not assessable | 812 (wrong: 0) |
| asserted on a page with no text | 0 |
| gold values never asserted | 341 |
| documents with no invoice | 0 |

## The three signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work. `contention` is the one that accuses a **pair**: when two of a reading's values claim one printed figure it flags both, because no label-free fact says which of the two is the intruder. Where the sibling is a correct reading that caps its precision near a half; where both belong to a row the page never printed, nothing it flags is correct and the row below says which of the two this run is.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 23 | 0 | 308 | 5768 | 100 % | 6.9 % |
| `arithmetic` | 252 | 1351 | 79 | 4417 | 15.7 % | 76.1 % |
| `contention` | 0 | 0 | 331 | 5768 | — | 0.0 % |
| `any of the three` | 252 | 1351 | 79 | 4417 | 15.7 % | 76.1 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 73.7 % | 98.2 % | 4496 | 79 |
| `medium` | `review` | 99.6 % | 94.9 % | 6076 | 308 |
| `low` | `review` | 100 % | 94.6 % | 6099 | 331 |
| `none` | `reject` | 100 % | 94.6 % | 6099 | 331 |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 341 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 812 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 0 of them are wrong, and nothing in the tables above counts those.
* **`grounding` missed 308 of the 331 wrong asserted value(s)** and flagged 23 of them. It asks whether a value is *on the page*, not whether it is in the *right place*: a reader that lifts a real figure out of the wrong column is fully grounded and completely wrong, and one that borrows a word from the other party's address is too. A **text** value is now resolved to one place rather than to whichever occurrence of each word came first, which is what makes its recorded spans a location at all; an amount or an identifier still resolves to every occurrence of itself. `contention` uses those places to catch the one wrong-column shape that is decidable without knowing which column is which — two values claiming one figure — and `docs/adr/0002_placement.md` carries the two shapes that leaves standing.
* The confidence levels are produced by fixed rules over the three signals, not by weights fitted to this corpus. That is why there are four and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
