# detector — gullible, hard rules

| | |
|---|---|
| run | `results/attacked-scanned-gullible` |
| answered by | `gullible` |
| baseline | `gullible` |
| saw | the page and the gold |
| severity | `hard` |
| documents | 168 |
| judged | 162 |
| no prediction | 6 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 18 | 12 |
| **fields right** | 0 | 132 |

| | |
|---|---:|
| prevalence | 18.5 % |
| precision | 100 % |
| recall | 60.0 % |
| F1 | 75.0 % |
| specificity | 100 % |
| localisation | 100 % (18 / 18) |

## Per rule

Precision only. A rule's recall is not a quantity this study can report: a document is wrong or not, and which rule *should* have caught it is not something the gold says.

| rule | fired on | of which wrong | precision |
|---|---:|---:|---:|
| `totals.gross_equals_line_sum` | 18 | 18 | 100 % |
| `totals.gross_equals_net_plus_vat` | 12 | 12 | 100 % |
| `lines.sum_matches_rate_net` | 5 | 5 | 100 % |
| `lines.sum_matches_rate_vat` | 5 | 5 | 100 % |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* 6 document(s) produced no invoice, so no rule could read one. They are outside every denominator above. The pipeline had already refused them on its own; counting them as catches would credit the invariants with that refusal.
* This is the **hard** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.


---

# detector — gullible, heuristic rules

| | |
|---|---|
| run | `results/attacked-scanned-gullible` |
| answered by | `gullible` |
| baseline | `gullible` |
| saw | the page and the gold |
| severity | `heuristic` |
| documents | 168 |
| judged | 162 |
| no prediction | 6 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 30 |
| **fields right** | 0 | 132 |

| | |
|---|---:|
| prevalence | 18.5 % |
| precision | — |
| recall | 0.0 % |
| F1 | — |
| specificity | 100 % |
| localisation | — (0 / 0) |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* **The detector caught nothing.** Every wrong document passed. A prediction can be internally consistent and still be wrong everywhere, and arithmetic cannot see the difference.
* 6 document(s) produced no invoice, so no rule could read one. They are outside every denominator above. The pipeline had already refused them on its own; counting them as catches would credit the invariants with that refusal.
* This is the **heuristic** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.
