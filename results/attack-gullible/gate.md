# the gate — gullible

| | |
|---|---|
| run | `results/attack-gullible` |
| answered by | `gullible` |
| saw | the page and the gold |
| values asserted | 6328 |
| of which wrong | 176 |
| assessed below | 5619 |
| of those, wrong | 176 |
| asserted but not assessable | 709 (wrong: 0) |
| asserted on a page with no text | 0 |
| gold values never asserted | 0 |
| documents with no invoice | 16 |

## The four signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work. `contention` is the one that accuses a **pair**: when two of a reading's values claim one printed figure it flags both, because no label-free fact says which of the two is the intruder. Where the sibling is a correct reading that caps its precision near a half; where both belong to a row the page never printed, nothing it flags is correct and the row below says which of the two this run is. `completeness` asks the opposite of grounding: not whether the value is on the page but whether the page kept printing it after the reading stopped.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 16 | 0 | 160 | 5443 | 100 % | 9.1 % |
| `arithmetic` | 128 | 2207 | 48 | 3236 | 5.5 % | 72.7 % |
| `contention` | 32 | 0 | 144 | 5443 | 100 % | 18.2 % |
| `completeness` | 1 | 0 | 175 | 5443 | 100 % | 0.6 % |
| `any of the four` | 129 | 2207 | 47 | 3236 | 5.5 % | 73.3 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 58.4 % | 98.6 % | 3283 | 47 |
| `medium` | `review` | 99.7 % | 97.2 % | 5602 | 159 |
| `low` | `review` | 100 % | 96.9 % | 5619 | 176 |
| `none` | `reject` | 100 % | 96.9 % | 5619 | 176 |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 0 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 709 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 0 of them are wrong, and nothing in the tables above counts those.
* 16 document(s) produced no invoice, so none of their fields was assessed. The pipeline had already refused them.
* **`grounding` missed 160 of the 176 wrong asserted value(s)** and flagged 16 of them. It asks whether a value is *on the page*, not whether it is in the *right place*: a reader that lifts a real figure out of the wrong column is fully grounded and completely wrong, and one that borrows a word from the other party's address is too. A **text** value is now resolved to one place rather than to whichever occurrence of each word came first, which is what makes its recorded spans a location at all; an amount or an identifier still resolves to every occurrence of itself. `contention` uses those places to catch the one wrong-column shape that is decidable without knowing which column is which — two values claiming one figure — and `docs/adr/0002_placement.md` carries the two shapes that leaves standing.
* `contention` flagged 32 asserted value(s), and **every one of them was already named by a hard rule**, so the gate reached the same verdict without it and what this signal adds here is the attribution, not the routing. It names the two fields that share a printed figure, where an arithmetic violation names the whole `lines` collection; the two catch overlapping populations and only the narrower one says *which* values are involved.
* `completeness` flagged 1 asserted value(s), and 1 of them (1 wrong) carried **no** other signal, so the gate would have accepted them. It is the one signal aimed at grounding's standing blind spot: a value that stops early is a real string, in the right place, and only the page's own wrapping says it is not the whole one.
* The confidence levels are produced by fixed rules over the four signals, not by weights fitted to this corpus. That is why there are four and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
