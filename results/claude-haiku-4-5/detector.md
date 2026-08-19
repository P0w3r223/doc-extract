# detector — claude-haiku-4-5, hard rules

| | |
|---|---|
| run | `results/claude-haiku-4-5` |
| answered by | `claude-haiku-4-5` |
| baseline | `claude` |
| saw | the page |
| severity | `hard` |
| documents | 108 |
| judged | 107 |
| no prediction | 1 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 32 | 10 |
| **fields right** | 0 | 65 |

| | |
|---|---:|
| prevalence | 39.3 % |
| precision | 100 % |
| recall | 76.2 % |
| F1 | 86.5 % |
| specificity | 100 % |
| localisation | 100 % (32 / 32) |

## Per rule

Precision only. A rule's recall is not a quantity this study can report: a document is wrong or not, and which rule *should* have caught it is not something the gold says.

| rule | fired on | of which wrong | precision |
|---|---:|---:|---:|
| `identifiers.iban_checksum` | 25 | 25 | 100 % |
| `lines.net_matches_quantity_times_price` | 9 | 9 | 100 % |
| `identifiers.nip_checksum` | 1 | 1 | 100 % |

## Read this before the tables

* 1 document(s) produced no invoice, so no rule could read one. They are outside every denominator above. The pipeline had already refused them on its own; counting them as catches would credit the invariants with that refusal.
* This is the **hard** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.


---

# detector — claude-haiku-4-5, heuristic rules

| | |
|---|---|
| run | `results/claude-haiku-4-5` |
| answered by | `claude-haiku-4-5` |
| baseline | `claude` |
| saw | the page |
| severity | `heuristic` |
| documents | 108 |
| judged | 107 |
| no prediction | 1 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 42 |
| **fields right** | 0 | 65 |

| | |
|---|---:|
| prevalence | 39.3 % |
| precision | — |
| recall | 0.0 % |
| F1 | — |
| specificity | 100 % |
| localisation | — (0 / 0) |

## Read this before the tables

* **The detector caught nothing.** Every wrong document passed. A prediction can be internally consistent and still be wrong everywhere, and arithmetic cannot see the difference.
* 1 document(s) produced no invoice, so no rule could read one. They are outside every denominator above. The pipeline had already refused them on its own; counting them as catches would credit the invariants with that refusal.
* This is the **heuristic** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.
