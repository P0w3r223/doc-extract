# detector — pattern, hard rules

| | |
|---|---|
| run | `results/foreign-pattern` |
| answered by | `pattern` |
| baseline | `pattern` |
| saw | the page |
| severity | `hard` |
| documents | 108 |
| judged | 0 |
| no prediction | 108 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 0 |
| **fields right** | 0 | 0 |

| | |
|---|---:|
| prevalence | — |
| precision | — |
| recall | — |
| F1 | — |
| specificity | — |
| localisation | — (0 / 0) |

## Read this before the tables

* 108 document(s) produced no invoice, so no rule could read one. They are outside every denominator above. The pipeline had already refused them on its own; counting them as catches would credit the invariants with that refusal.
* This is the **hard** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.


---

# detector — pattern, heuristic rules

| | |
|---|---|
| run | `results/foreign-pattern` |
| answered by | `pattern` |
| baseline | `pattern` |
| saw | the page |
| severity | `heuristic` |
| documents | 108 |
| judged | 0 |
| no prediction | 108 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 0 |
| **fields right** | 0 | 0 |

| | |
|---|---:|
| prevalence | — |
| precision | — |
| recall | — |
| F1 | — |
| specificity | — |
| localisation | — (0 / 0) |

## Read this before the tables

* 108 document(s) produced no invoice, so no rule could read one. They are outside every denominator above. The pipeline had already refused them on its own; counting them as catches would credit the invariants with that refusal.
* This is the **heuristic** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.
