# the gate — gullible

| | |
|---|---|
| run | `results/attacked-scanned-gullible` |
| answered by | `gullible` |
| saw | the page and the gold |
| values asserted | 8745 |
| of which wrong | 66 |
| gold values never asserted | 0 |
| asserted but not assessable | 1149 |
| documents with no invoice | 6 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 6 | 6048 | 60 | 2631 | 0.1 % | 9.1 % |
| `arithmetic` | 48 | 889 | 18 | 7790 | 5.1 % | 72.7 % |
| `either` | 48 | 6937 | 18 | 1742 | 0.7 % | 72.7 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 20.1 % | 99.0 % | 1760 | 18 |
| `medium` | `review` | 30.8 % | 97.8 % | 2691 | 60 |
| `low` | `review` | 30.8 % | 97.6 % | 2697 | 66 |
| `none` | `reject` | 100 % | 99.2 % | 8745 | 66 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 0 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 1149 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. They are values a model can get wrong, and nothing above measures whether it did.
* 6 document(s) produced no invoice, so none of their fields was assessed. The pipeline had already refused them.
* **6048 of the 8745 assessed value(s) (69.2 %) sit on a page with no text layer at all.** Grounding resolves a value against page text and there is none, so it returns `UNGROUNDED` for every one of them — correct or not. Nothing here distinguishes *this value is not on the page* from *there was no page to look in*, which means the coverage figure above is partly a measurement of the missing text layer rather than of the reader. Read the accuracy at `none` — accepting everything — as the comparison that is not affected by it.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
