# the gate — oracle

| | |
|---|---|
| run | `results/scanned-oracle` |
| answered by | `oracle` |
| saw | the gold |
| values asserted | 6674 |
| of which wrong | 0 |
| assessed below | 1903 |
| of those, wrong | 0 |
| asserted but not assessable | 782 (wrong: 0) |
| asserted on a page with no text | 3989 (wrong: 0) |
| gold values never asserted | 0 |
| documents with no invoice | 0 |

## The two signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 0 | 0 | 0 | 1903 | — | — |
| `arithmetic` | 0 | 0 | 0 | 1903 | — | — |
| `either` | 0 | 0 | 0 | 1903 | — | — |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 100 % | 100 % | 1903 | 0 |
| `medium` | `review` | 100 % | 100 % | 1903 | 0 |
| `low` | `review` | 100 % | 100 % | 1903 | 0 |
| `none` | `reject` | 100 % | 100 % | 1903 | 0 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 0 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 782 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 0 of them are wrong, and nothing in the tables above counts those.
* **3989 of the 6674 asserted value(s) (59.8 %) sit on a page with no text layer at all, and are outside the curve.** Grounding resolves a value against page text and there is none, so it answers `NO_TEXT` — *I could not ask* — rather than `UNGROUNDED`, which would have claimed the value is missing from the page. They are routed `review` and carry no confidence, so every figure above is over the 1903 value(s) this pipeline could actually assess, and 0 wrong value(s) sit in the excluded set where nothing measures them. **The gate has no signal at all on those**, and that is a statement about the page rather than about the reader: a recogniser in front of the model brings the signal back.
* **Against the ungated policy.** Accepting every asserted value — the 1903 below plus the 4771 excluded from them — is 100 % accurate. The `high` row is 100 %, so on this corpus auto-accepting the gate's confident bucket is **more accurate than not gating at all**, which is what a gate is for. The `none` row is *not* that comparison: it accepts everything the gate could assess, which is a different set.
* **Nothing asserted was wrong**, so the gate had nothing to catch. Accuracy is 100 % at every level and the curve is flat by construction; it says the gate does not block correct work, and nothing about whether it blocks incorrect work.
* The confidence levels are produced by fixed rules over the two signals, not by weights fitted to this corpus. That is why there are four of them and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
