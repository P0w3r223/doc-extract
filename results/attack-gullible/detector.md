# detector — gullible, hard rules

| | |
|---|---|
| run | `results/attack-gullible` |
| answered by | `gullible` |
| baseline | `gullible` |
| saw | the page and the gold |
| severity | `hard` |
| documents | 112 |
| judged | 96 |
| no prediction | 16 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 48 | 32 |
| **fields right** | 0 | 16 |

| | |
|---|---:|
| prevalence | 83.3 % |
| precision | 100 % |
| recall | 60.0 % |
| F1 | 75.0 % |
| specificity | 100 % |
| localisation | 100 % (48 / 48) |

## Per rule

Precision only. A rule's recall is not a quantity this study can report: a document is wrong or not, and which rule *should* have caught it is not something the gold says.

| rule | fired on | of which wrong | precision |
|---|---:|---:|---:|
| `totals.gross_equals_line_sum` | 48 | 48 | 100 % |
| `totals.gross_equals_net_plus_vat` | 32 | 32 | 100 % |
| `lines.sum_matches_rate_net` | 15 | 15 | 100 % |
| `lines.sum_matches_rate_vat` | 15 | 15 | 100 % |

## Read this before the tables

* 16 document(s) produced no invoice, so no rule could read one. They are outside every denominator above. The pipeline had already refused them on its own; counting them as catches would credit the invariants with that refusal.
* This is the **hard** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.


---

# detector — gullible, heuristic rules

| | |
|---|---|
| run | `results/attack-gullible` |
| answered by | `gullible` |
| baseline | `gullible` |
| saw | the page and the gold |
| severity | `heuristic` |
| documents | 112 |
| judged | 96 |
| no prediction | 16 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 80 |
| **fields right** | 0 | 16 |

| | |
|---|---:|
| prevalence | 83.3 % |
| precision | — |
| recall | 0.0 % |
| F1 | — |
| specificity | 100 % |
| localisation | — (0 / 0) |

## Read this before the tables

* **The detector caught nothing.** Every wrong document passed. A prediction can be internally consistent and still be wrong everywhere, and arithmetic cannot see the difference.
* 16 document(s) produced no invoice, so no rule could read one. They are outside every denominator above. The pipeline had already refused them on its own; counting them as catches would credit the invariants with that refusal.
* This is the **heuristic** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.
