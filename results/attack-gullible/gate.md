# the gate — gullible

| | |
|---|---|
| run | `results/attack-gullible` |
| answered by | `gullible` |
| saw | the page and the gold |
| values asserted | 5619 |
| of which wrong | 176 |
| gold values never asserted | 0 |
| asserted but not assessable | 709 |
| asserted on a page with no text | 0 |
| documents with no invoice | 16 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 16 | 0 | 160 | 5443 | 100 % | 9.1 % |
| `arithmetic` | 128 | 2207 | 48 | 3236 | 5.5 % | 72.7 % |
| `either` | 128 | 2207 | 48 | 3236 | 5.5 % | 72.7 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 58.4 % | 98.5 % | 3284 | 48 |
| `medium` | `review` | 99.7 % | 97.1 % | 5603 | 160 |
| `low` | `review` | 100 % | 96.9 % | 5619 | 176 |
| `none` | `reject` | 100 % | 96.9 % | 5619 | 176 |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 0 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 709 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. They are values a model can get wrong, and nothing above measures whether it did.
* 16 document(s) produced no invoice, so none of their fields was assessed. The pipeline had already refused them.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
