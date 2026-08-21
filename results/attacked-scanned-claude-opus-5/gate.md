# the gate — claude-opus-5

| | |
|---|---|
| run | `results/attacked-scanned-claude-opus-5` |
| answered by | `claude-opus-5` |
| saw | the page |
| values asserted | 10269 |
| of which wrong | 42 |
| assessed below | 3024 |
| of those, wrong | 14 |
| asserted but not assessable | 1197 (wrong: 0) |
| asserted on a page with no text | 6048 (wrong: 28) |
| gold values never asserted | 0 |
| documents with no invoice | 0 |

## The three signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work. `contention` is the one whose precision is bounded by construction: when two of a reading's values claim one printed figure it flags **both**, because no label-free fact says which of the two is the intruder, so about half of what it flags is the correct sibling of a wrong value.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 9 | 0 | 5 | 3010 | 100 % | 64.3 % |
| `arithmetic` | 0 | 0 | 14 | 3010 | — | 0.0 % |
| `contention` | 0 | 0 | 14 | 3010 | — | 0.0 % |
| `any of the three` | 9 | 0 | 5 | 3010 | 100 % | 64.3 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 99.7 % | 99.8 % | 3015 | 5 |
| `medium` | `review` | 99.7 % | 99.8 % | 3015 | 5 |
| `low` | `review` | 100 % | 99.5 % | 3024 | 14 |
| `none` | `reject` | 100 % | 99.5 % | 3024 | 14 |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 0 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 1197 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 0 of them are wrong, and nothing in the tables above counts those.
* **6048 of the 10269 asserted value(s) (58.9 %) sit on a page with no text layer at all, and are outside the curve.** Grounding resolves a value against page text and there is none, so it answers `NO_TEXT` — *I could not ask* — rather than `UNGROUNDED`, which would have claimed the value is missing from the page. They are routed `review` and carry no confidence, so every figure above is over the 3024 value(s) this pipeline could actually assess, and 28 wrong value(s) sit in the excluded set where nothing measures them. **The gate has no signal at all on those**, and that is a statement about the page rather than about the reader: a recogniser in front of the model brings the signal back.
* **Against the ungated policy.** Accepting every asserted value — the 3024 below plus the 7245 excluded from them — is 99.6 % accurate. The `high` row is 99.8 %, so on this corpus auto-accepting the gate's confident bucket is **more accurate than not gating at all**, which is what a gate is for. The `none` row is *not* that comparison: it accepts everything the gate could assess, which is a different set.
* **`arithmetic` flagged nothing at all**, while 14 asserted value(s) were wrong. No identity was broken: a prediction can be internally consistent and still be wrong everywhere, which is what a constant or a wholly-invented answer looks like from the arithmetic's side.
* The confidence levels are produced by fixed rules over the three signals, not by weights fitted to this corpus. That is why there are four and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
