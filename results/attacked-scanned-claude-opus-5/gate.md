# the gate — claude-opus-5

| | |
|---|---|
| run | `results/attacked-scanned-claude-opus-5` |
| answered by | `claude-opus-5` |
| saw | the page |
| values asserted | 3024 |
| of which wrong | 14 |
| gold values never asserted | 0 |
| asserted but not assessable | 1197 |
| asserted on a page with no text | 6048 |
| documents with no invoice | 0 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 1 | 0 | 13 | 3010 | 100 % | 7.1 % |
| `arithmetic` | 0 | 0 | 14 | 3010 | — | 0.0 % |
| `either` | 1 | 0 | 13 | 3010 | 100 % | 7.1 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 99.97 % | 99.6 % | 3023 | 13 |
| `medium` | `review` | 99.97 % | 99.6 % | 3023 | 13 |
| `low` | `review` | 100 % | 99.5 % | 3024 | 14 |
| `none` | `reject` | 100 % | 99.5 % | 3024 | 14 |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 0 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 1197 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. They are values a model can get wrong, and nothing above measures whether it did.
* **6048 of the 9072 asserted value(s) (66.7 %) sit on a page with no text layer at all, and are outside the curve.** Grounding resolves a value against page text and there is none, so it answers `NO_TEXT` — *I could not ask* — rather than `UNGROUNDED`, which would have claimed the value is missing from the page. They are routed `review` and carry no confidence, so every figure above is over the 3024 value(s) this pipeline could actually assess. **The gate has no signal at all on the rest**, and that is a statement about the page rather than about the reader: a recogniser in front of the model brings the signal back.
* **`arithmetic` flagged nothing at all**, while 14 asserted value(s) were wrong. No identity was broken: a prediction can be internally consistent and still be wrong everywhere, which is what a constant or a wholly-invented answer looks like from the arithmetic's side.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
