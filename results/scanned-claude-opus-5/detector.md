# detector — claude-opus-5, hard rules

| | |
|---|---|
| run | `results/scanned-claude-opus-5` |
| answered by | `claude-opus-5` |
| baseline | `claude` |
| saw | the page |
| severity | `hard` |
| documents | 108 |
| judged | 108 |
| no prediction | 0 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 1 | 0 |
| **fields right** | 0 | 107 |

| | |
|---|---:|
| prevalence | 0.9 % |
| precision | 100 % |
| recall | 100 % |
| F1 | 100 % |
| specificity | 100 % |
| localisation | 100 % (1 / 1) |

## Per rule

Precision only. A rule's recall is not a quantity this study can report: a document is wrong or not, and which rule *should* have caught it is not something the gold says.

| rule | fired on | of which wrong | precision |
|---|---:|---:|---:|
| `identifiers.iban_checksum` | 1 | 1 | 100 % |

## Read this before the tables

* This is the **hard** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.


---

# detector — claude-opus-5, heuristic rules

| | |
|---|---|
| run | `results/scanned-claude-opus-5` |
| answered by | `claude-opus-5` |
| baseline | `claude` |
| saw | the page |
| severity | `heuristic` |
| documents | 108 |
| judged | 108 |
| no prediction | 0 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 1 |
| **fields right** | 0 | 107 |

| | |
|---|---:|
| prevalence | 0.9 % |
| precision | — |
| recall | 0.0 % |
| F1 | — |
| specificity | 100 % |
| localisation | — (0 / 0) |

## Read this before the tables

* **The detector caught nothing.** Every wrong document passed. A prediction can be internally consistent and still be wrong everywhere, and arithmetic cannot see the difference.
* This is the **heuristic** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.
