# detector — oracle, hard rules

| | |
|---|---|
| run | `results/attack-oracle` |
| answered by | `oracle` |
| baseline | `oracle` |
| saw | the gold |
| severity | `hard` |
| documents | 112 |
| judged | 112 |
| no prediction | 0 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 0 |
| **fields right** | 0 | 112 |

| | |
|---|---:|
| prevalence | 0.0 % |
| precision | — |
| recall | — |
| F1 | — |
| specificity | 100 % |
| localisation | — (0 / 0) |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* **Nothing was wrong on any judged document, so there was nothing to detect.** Precision and recall have no denominator and print as a dash. The one number this run does establish is the false-positive rate: 0 of 112 correctly-read documents were flagged — a gate that does not block correct work. It says nothing about whether the gate catches incorrect work.
* This is the **hard** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.


---

# detector — oracle, heuristic rules

| | |
|---|---|
| run | `results/attack-oracle` |
| answered by | `oracle` |
| baseline | `oracle` |
| saw | the gold |
| severity | `heuristic` |
| documents | 112 |
| judged | 112 |
| no prediction | 0 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 0 |
| **fields right** | 0 | 112 |

| | |
|---|---:|
| prevalence | 0.0 % |
| precision | — |
| recall | — |
| F1 | — |
| specificity | 100 % |
| localisation | — (0 / 0) |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* **Nothing was wrong on any judged document, so there was nothing to detect.** Precision and recall have no denominator and print as a dash. The one number this run does establish is the false-positive rate: 0 of 112 correctly-read documents were flagged — a gate that does not block correct work. It says nothing about whether the gate catches incorrect work.
* This is the **heuristic** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.
