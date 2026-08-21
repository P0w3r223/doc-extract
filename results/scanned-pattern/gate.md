# the gate — pattern

| | |
|---|---|
| run | `results/scanned-pattern` |
| answered by | `pattern` |
| saw | the page |
| values asserted | 1913 |
| of which wrong | 156 |
| assessed below | 1663 |
| of those, wrong | 156 |
| asserted but not assessable | 250 (wrong: 0) |
| asserted on a page with no text | 0 |
| gold values never asserted | 140 |
| documents with no invoice | 74 |

## The four signals, scored apart

Field-level detectors of a wrong asserted value. They are complements with very different shapes, and a reader who saw only their combination could not tell which did the work. `contention` is the one that accuses a **pair**: when two of a reading's values claim one printed figure it flags both, because no label-free fact says which of the two is the intruder. Where the sibling is a correct reading that caps its precision near a half; where both belong to a row the page never printed, nothing it flags is correct and the row below says which of the two this run is. `completeness` asks the opposite of grounding: not whether the value is on the page but whether the page kept printing it after the reading stopped.

| signal | TP | FP | FN | TN | precision | recall |
|---|---:|---:|---:|---:|---:|---:|
| `grounding` | 10 | 0 | 146 | 1507 | 100 % | 6.4 % |
| `arithmetic` | 125 | 671 | 31 | 836 | 15.7 % | 80.1 % |
| `contention` | 0 | 0 | 156 | 1507 | — | 0.0 % |
| `completeness` | 73 | 0 | 83 | 1507 | 100 % | 46.8 % |
| `any of the four` | 156 | 671 | 0 | 836 | 18.9 % | 100 % |

## Coverage and accuracy

Cumulative: each row accepts everything at its level **and above**. `leaked` counts the wrong values accepted, which is what a gate is actually judged on.

| accept down to | route | coverage | accuracy | accepted | leaked |
|---|---|---:|---:|---:|---:|
| `high` | `accept` | 50.3 % | 100 % | 836 | 0 |
| `medium` | `review` | 95.0 % | 95.4 % | 1580 | 73 |
| `low` | `review` | 100 % | 90.6 % | 1663 | 156 |
| `none` | `reject` | 100 % | 90.6 % | 1663 | 156 |

## Read this before the tables

* **Coverage is over the values the model asserted, not over the document.** A field it left `null` cannot be grounded, so it carries no confidence and sits outside every denominator above. 140 gold value(s) were never asserted at all, and no signal here can see them — a model that answered less would score better on this curve.
* 250 asserted value(s) are **outside the curve** because grounding declines to ask about them: `kind` is an FA(3) code the page never prints, and a non-numeric rate is an exemption code each issuer abbreviates their own way. 0 of them are wrong, and nothing in the tables above counts those.
* 74 document(s) produced no invoice, so none of their fields was assessed. The pipeline had already refused them.
* **`grounding` missed 146 of the 156 wrong asserted value(s)** and flagged 10 of them. It asks whether a value is *on the page*, not whether it is in the *right place*: a reader that lifts a real figure out of the wrong column is fully grounded and completely wrong, and one that borrows a word from the other party's address is too. A **text** value is now resolved to one place rather than to whichever occurrence of each word came first, which is what makes its recorded spans a location at all; an amount or an identifier still resolves to every occurrence of itself. `contention` uses those places to catch the one wrong-column shape that is decidable without knowing which column is which — two values claiming one figure — and `docs/adr/0002_placement.md` carries the two shapes that leaves standing.
* `completeness` flagged 73 asserted value(s), and 31 of them (31 wrong) carried **no** other signal, so the gate would have accepted them. It is the one signal aimed at grounding's standing blind spot: a value that stops early is a real string, in the right place, and only the page's own wrapping says it is not the whole one.
* The confidence levels are produced by fixed rules over the four signals, not by weights fitted to this corpus. That is why there are four and not a smooth sweep: a fitted score would draw a better curve here and would be measuring its own training set.
