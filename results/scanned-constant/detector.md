# detector — constant, hard rules

| | |
|---|---|
| run | `results/scanned-constant` |
| answered by | `constant` |
| baseline | `constant` |
| saw | nothing |
| severity | `hard` |
| documents | 108 |
| judged | 108 |
| no prediction | 0 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 108 |
| **fields right** | 0 | 0 |

| | |
|---|---:|
| prevalence | 100 % |
| precision | — |
| recall | 0.0 % |
| F1 | — |
| specificity | — |
| localisation | — (0 / 0) |

## Read this before the tables

* **Every one of the 108 judged documents was wrong, so a false positive was impossible.** Precision has no adversary here and cannot be read as one: a rule that fired on *every* document would print the same figure. Specificity, whose denominator is the correct documents, prints a dash for the same reason. **The rate this arm establishes is the recall.** It is the mirror of a run with nothing wrong in it, where the recall is the undefined one — and it is the more flattering of the two, which is why it is printed rather than left to be noticed.
* **The detector caught nothing.** Every wrong document passed. A prediction can be internally consistent and still be wrong everywhere, and arithmetic cannot see the difference.
* This is the **hard** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.


---

# detector — constant, heuristic rules

| | |
|---|---|
| run | `results/scanned-constant` |
| answered by | `constant` |
| baseline | `constant` |
| saw | nothing |
| severity | `heuristic` |
| documents | 108 |
| judged | 108 |
| no prediction | 0 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 108 |
| **fields right** | 0 | 0 |

| | |
|---|---:|
| prevalence | 100 % |
| precision | — |
| recall | 0.0 % |
| F1 | — |
| specificity | — |
| localisation | — (0 / 0) |

## Read this before the tables

* **Every one of the 108 judged documents was wrong, so a false positive was impossible.** Precision has no adversary here and cannot be read as one: a rule that fired on *every* document would print the same figure. Specificity, whose denominator is the correct documents, prints a dash for the same reason. **The rate this arm establishes is the recall.** It is the mirror of a run with nothing wrong in it, where the recall is the undefined one — and it is the more flattering of the two, which is why it is printed rather than left to be noticed.
* **The detector caught nothing.** Every wrong document passed. A prediction can be internally consistent and still be wrong everywhere, and arithmetic cannot see the difference.
* This is the **heuristic** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.
