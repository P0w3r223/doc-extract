# detector — pattern, hard rules

| | |
|---|---|
| run | `results/scanned-pattern` |
| answered by | `pattern` |
| baseline | `pattern` |
| saw | the page |
| severity | `hard` |
| documents | 108 |
| judged | 34 |
| no prediction | 74 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 13 | 21 |
| **fields right** | 0 | 0 |

| | |
|---|---:|
| prevalence | 100 % |
| precision | 100 % |
| recall | 38.2 % |
| F1 | 55.3 % |
| specificity | — |
| localisation | 100 % (13 / 13) |

## Per rule

Precision only. A rule's recall is not a quantity this study can report: a document is wrong or not, and which rule *should* have caught it is not something the gold says.

| rule | fired on | of which wrong | precision |
|---|---:|---:|---:|
| `lines.net_matches_quantity_times_price` | 13 | 13 | 100 % |

## Read this before the tables

* **Every one of the 34 judged documents was wrong, so a false positive was impossible.** Precision prints 100 %, and it has no adversary here and cannot be read as one: a rule that fired on *every* document would print the same figure. Specificity, whose denominator is the correct documents, prints a dash for the same reason. **The rate this arm establishes is the recall.** It is the mirror of a run with nothing wrong in it, where the recall is the undefined one — and it is the more flattering of the two, which is why it is printed rather than left to be noticed.
* 74 document(s) produced no invoice, so no rule could read one. They are outside every denominator above. The pipeline had already refused them on its own; counting them as catches would credit the invariants with that refusal.
* This is the **hard** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.


---

# detector — pattern, heuristic rules

| | |
|---|---|
| run | `results/scanned-pattern` |
| answered by | `pattern` |
| baseline | `pattern` |
| saw | the page |
| severity | `heuristic` |
| documents | 108 |
| judged | 34 |
| no prediction | 74 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 34 |
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

* **Every one of the 34 judged documents was wrong, so a false positive was impossible.** Precision has no adversary here and cannot be read as one: a rule that fired on *every* document would print the same figure. Specificity, whose denominator is the correct documents, prints a dash for the same reason. **The rate this arm establishes is the recall.** It is the mirror of a run with nothing wrong in it, where the recall is the undefined one — and it is the more flattering of the two, which is why it is printed rather than left to be noticed.
* **The detector caught nothing.** Every wrong document passed. A prediction can be internally consistent and still be wrong everywhere, and arithmetic cannot see the difference.
* 74 document(s) produced no invoice, so no rule could read one. They are outside every denominator above. The pipeline had already refused them on its own; counting them as catches would credit the invariants with that refusal.
* This is the **heuristic** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.
