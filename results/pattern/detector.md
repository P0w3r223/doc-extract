# detector — pattern, hard rules

| | |
|---|---|
| run | `results/pattern` |
| answered by | `pattern` |
| baseline | `pattern` |
| saw | the page |
| severity | `hard` |
| documents | 108 |
| judged | 104 |
| no prediction | 4 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 27 | 42 |
| **fields right** | 0 | 35 |

| | |
|---|---:|
| prevalence | 66.3 % |
| precision | 100 % |
| recall | 39.1 % |
| F1 | 56.2 % |
| specificity | 100 % |
| localisation | 100 % (27 / 27) |

## Per rule

Precision only. A rule's recall is not a quantity this study can report: a document is wrong or not, and which rule *should* have caught it is not something the gold says.

| rule | fired on | of which wrong | precision |
|---|---:|---:|---:|
| `lines.net_matches_quantity_times_price` | 26 | 26 | 100 % |
| `lines.sum_matches_rate_net` | 1 | 1 | 100 % |
| `lines.sum_matches_rate_vat` | 1 | 1 | 100 % |
| `totals.gross_equals_line_sum` | 1 | 1 | 100 % |

## Read this before the tables

* 4 document(s) produced no invoice, so no rule could read one. They are outside every denominator above. The pipeline had already refused them on its own; counting them as catches would credit the invariants with that refusal.
* This is the **hard** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.


---

# detector — pattern, heuristic rules

| | |
|---|---|
| run | `results/pattern` |
| answered by | `pattern` |
| baseline | `pattern` |
| saw | the page |
| severity | `heuristic` |
| documents | 108 |
| judged | 104 |
| no prediction | 4 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 69 |
| **fields right** | 0 | 35 |

| | |
|---|---:|
| prevalence | 66.3 % |
| precision | — |
| recall | 0.0 % |
| F1 | — |
| specificity | 100 % |
| localisation | — (0 / 0) |

## Read this before the tables

* **The detector caught nothing.** Every wrong document passed. A prediction can be internally consistent and still be wrong everywhere, and arithmetic cannot see the difference.
* 4 document(s) produced no invoice, so no rule could read one. They are outside every denominator above. The pipeline had already refused them on its own; counting them as catches would credit the invariants with that refusal.
* This is the **heuristic** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.
