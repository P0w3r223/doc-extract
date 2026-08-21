# the gate — pattern

| | |
|---|---|
| run | `results/attacked-scanned-pattern` |
| answered by | `pattern` |
| saw | the page |
| values asserted | 3168 |
| of which wrong | 228 |
| assessed below | 2769 |
| of those, wrong | 228 |
| asserted but not assessable | 399 (wrong: 0) |
| asserted on a page with no text | 0 |
| gold values never asserted | 255 |
| documents with no invoice | 112 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 21 | 0 | 207 | 2541 | 100 % | 9.2 % |
| `arithmetic` | 210 | 1204 | 18 | 1337 | 14.9 % | 92.1 % |
| `either` | 210 | 1204 | 18 | 1337 | 14.9 % | 92.1 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 48.9 % | 98.7 % | 1355 | 18 |
| `medium` | `review` | 99.2 % | 92.5 % | 2748 | 207 |
| `low` | `review` | 100 % | 91.8 % | 2769 | 228 |
| `none` | `reject` | 100 % | 91.8 % | 2769 | 228 |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 255 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 399 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 0 of them are wrong, and nothing in the tables above counts those.
* 112 document(s) produced no invoice, so none of their fields was assessed. The pipeline had already refused them.
* **`grounding` missed 207 of the 228 wrong asserted value(s)** and flagged 21 of them. It asks whether a value is *on the page*, not whether it is in the *right place*: a reader that lifts a real figure out of the wrong column is fully grounded and completely wrong, and one that borrows a word from the other party's address is too. A value is now resolved to **one place** rather than to whichever occurrence of each word came first, which is what makes the recorded spans a location at all — but the geometric check that would use them is still not built, and `docs/adr/0002_placement.md` carries what it turned out to need.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
