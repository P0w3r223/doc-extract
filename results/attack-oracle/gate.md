# the gate — oracle

| | |
|---|---|
| run | `results/attack-oracle` |
| answered by | `oracle` |
| saw | the gold |
| values asserted | 6440 |
| of which wrong | 0 |
| gold values never asserted | 0 |
| asserted but not assessable | 812 |
| asserted on a page with no text | 0 |
| documents with no invoice | 0 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 0 | 0 | 0 | 6440 | — | — |
| `arithmetic` | 0 | 0 | 0 | 6440 | — | — |
| `either` | 0 | 0 | 0 | 6440 | — | — |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 100 % | 100 % | 6440 | 0 |
| `medium` | `review` | 100 % | 100 % | 6440 | 0 |
| `low` | `review` | 100 % | 100 % | 6440 | 0 |
| `none` | `reject` | 100 % | 100 % | 6440 | 0 |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 0 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 812 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. They are values a model can get wrong, and nothing above measures whether it did.
* **Nothing asserted was wrong**, so the gate had nothing to catch. Accuracy is 100 % at every level and the curve is flat by construction; it says the gate does not block correct work, and nothing about whether it blocks incorrect work.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
