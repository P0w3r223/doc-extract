# detector — claude-haiku-4-5, hard rules

| | |
|---|---|
| run | `results/foreign-claude-haiku-4-5` |
| answered by | `claude-haiku-4-5` |
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
| **fields wrong** | 28 | 28 |
| **fields right** | 0 | 52 |

| | |
|---|---:|
| prevalence | 51.9 % |
| precision | 100 % |
| recall | 50.0 % |
| F1 | 66.7 % |
| specificity | 100 % |
| localisation | 100 % (28 / 28) |

## Per rule

Precision only. A rule's recall is not a quantity this study can report: a document is wrong or not, and which rule *should* have caught it is not something the gold says.

| rule | fired on | of which wrong | precision |
|---|---:|---:|---:|
| `lines.net_matches_quantity_times_price` | 16 | 16 | 100 % |
| `identifiers.iban_checksum` | 11 | 11 | 100 % |
| `lines.sum_matches_rate_net` | 5 | 5 | 100 % |
| `totals.gross_equals_line_sum` | 2 | 2 | 100 % |
| `identifiers.nip_checksum` | 1 | 1 | 100 % |
| `lines.sum_matches_rate_vat` | 1 | 1 | 100 % |
| `lines.vat_matches_rate` | 1 | 1 | 100 % |

## Read this before the tables

* This is the **hard** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.


---

# detector — claude-haiku-4-5, heuristic rules

| | |
|---|---|
| run | `results/foreign-claude-haiku-4-5` |
| answered by | `claude-haiku-4-5` |
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
| **fields wrong** | 2 | 54 |
| **fields right** | 0 | 52 |

| | |
|---|---:|
| prevalence | 51.9 % |
| precision | 100 % |
| recall | 3.6 % |
| F1 | 6.9 % |
| specificity | 100 % |
| localisation | 100 % (2 / 2) |

## Per rule

Precision only. A rule's recall is not a quantity this study can report: a document is wrong or not, and which rule *should* have caught it is not something the gold says.

| rule | fired on | of which wrong | precision |
|---|---:|---:|---:|
| `dates.issue_follows_sale` | 2 | 2 | 100 % |

## Read this before the tables

* This is the **heuristic** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.
