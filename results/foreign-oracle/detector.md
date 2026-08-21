# detector — oracle, hard rules

| | |
|---|---|
| run | `results/foreign-oracle` |
| answered by | `oracle` |
| baseline | `oracle` |
| saw | the gold |
| severity | `hard` |
| documents | 108 |
| judged | 108 |
| no prediction | 0 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 0 |
| **fields right** | 0 | 108 |

| | |
|---|---:|
| prevalence | 0.0 % |
| precision | — |
| recall | — |
| F1 | — |
| specificity | 100 % |
| localisation | — (0 / 0) |

## Read this before the tables

* **Nothing was wrong on any judged document, so there was nothing to detect.** Precision and recall have no denominator and print as a dash. The one number this run does establish is the false-positive rate: 0 of 108 correctly-read documents were flagged — a gate that does not block correct work. It says nothing about whether the gate catches incorrect work.
* This is the **hard** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.


---

# detector — oracle, heuristic rules

| | |
|---|---|
| run | `results/foreign-oracle` |
| answered by | `oracle` |
| baseline | `oracle` |
| saw | the gold |
| severity | `heuristic` |
| documents | 108 |
| judged | 108 |
| no prediction | 0 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 0 |
| **fields right** | 0 | 108 |

| | |
|---|---:|
| prevalence | 0.0 % |
| precision | — |
| recall | — |
| F1 | — |
| specificity | 100 % |
| localisation | — (0 / 0) |

## Read this before the tables

* **Nothing was wrong on any judged document, so there was nothing to detect.** Precision and recall have no denominator and print as a dash. The one number this run does establish is the false-positive rate: 0 of 108 correctly-read documents were flagged — a gate that does not block correct work. It says nothing about whether the gate catches incorrect work.
* This is the **heuristic** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.
