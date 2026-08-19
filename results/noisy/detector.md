# detector — noisy, hard rules

| | |
|---|---|
| run | `results/noisy` |
| answered by | `noisy` |
| baseline | `noisy` |
| saw | the gold |
| severity | `hard` |
| documents | 108 |
| judged | 108 |
| no prediction | 0 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 60 | 7 |
| **fields right** | 0 | 41 |

| | |
|---|---:|
| prevalence | 62.0 % |
| precision | 100 % |
| recall | 89.6 % |
| F1 | 94.5 % |
| specificity | 100 % |
| localisation | 100 % (60 / 60) |

## Per rule

Precision only. A rule's recall is not a quantity this study can report: a document is wrong or not, and which rule *should* have caught it is not something the gold says.

| rule | fired on | of which wrong | precision |
|---|---:|---:|---:|
| `totals.gross_equals_line_sum` | 29 | 29 | 100 % |
| `lines.sum_matches_rate_net` | 27 | 27 | 100 % |
| `lines.sum_matches_rate_vat` | 27 | 27 | 100 % |
| `totals.gross_equals_net_plus_vat` | 24 | 24 | 100 % |
| `totals.vat_matches_rate` | 23 | 23 | 100 % |
| `lines.net_matches_quantity_times_price` | 16 | 16 | 100 % |
| `identifiers.nip_checksum` | 14 | 14 | 100 % |
| `lines.vat_matches_rate` | 14 | 14 | 100 % |
| `identifiers.iban_checksum` | 13 | 13 | 100 % |
| `totals.non_correction_amounts_non_negative` | 2 | 2 | 100 % |

## Per injected error kind

`isolated` counts only the documents where this was the **only** kind injected, so a firing is attributable to it. `marginal` counts every document carrying the kind and is contaminated by whatever else landed beside it. Read the isolated column.

| kind | isolated | n | marginal | n | |
|---|---:|---:|---:|---:|---|
| `total_transposed` | 100 % | 5 | 100 % | 9 |  |
| `vat_cent` | 100 % | 10 | 100 % | 15 |  |
| `rate_swapped` | 100 % | 4 | 100 % | 8 |  |
| `line_dropped` | 100 % | 2 | 100 % | 7 |  |
| `line_transposed` | 100 % | 5 | 100 % | 16 |  |
| `nip_digit` | 100 % | 8 | 100 % | 14 |  |
| `account_digit` | 100 % | 6 | 100 % | 13 |  |
| `date_shifted` | 0.0 % | 2 | 50.0 % | 4 | declared invisible |
| `name_truncated` | 0.0 % | 5 | 37.5 % | 8 | declared invisible |

## Read this before the tables

* This is the **hard** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.


---

# detector — noisy, heuristic rules

| | |
|---|---|
| run | `results/noisy` |
| answered by | `noisy` |
| baseline | `noisy` |
| saw | the gold |
| severity | `heuristic` |
| documents | 108 |
| judged | 108 |
| no prediction | 0 |

## Does "the arithmetic holds" predict "the fields are right"?

The detector is `invariants.check` run on the **prediction**, never on the gold: the signal has to be available at inference time on a document nobody annotated.

| | flagged | silent |
|---|---:|---:|
| **fields wrong** | 0 | 67 |
| **fields right** | 0 | 41 |

| | |
|---|---:|
| prevalence | 62.0 % |
| precision | — |
| recall | 0.0 % |
| F1 | — |
| specificity | 100 % |
| localisation | — (0 / 0) |

## Per injected error kind

`isolated` counts only the documents where this was the **only** kind injected, so a firing is attributable to it. `marginal` counts every document carrying the kind and is contaminated by whatever else landed beside it. Read the isolated column.

| kind | isolated | n | marginal | n | |
|---|---:|---:|---:|---:|---|
| `total_transposed` | 0.0 % | 5 | 0.0 % | 9 |  |
| `vat_cent` | 0.0 % | 10 | 0.0 % | 15 |  |
| `rate_swapped` | 0.0 % | 4 | 0.0 % | 8 |  |
| `line_dropped` | 0.0 % | 2 | 0.0 % | 7 |  |
| `line_transposed` | 0.0 % | 5 | 0.0 % | 16 |  |
| `nip_digit` | 0.0 % | 8 | 0.0 % | 14 |  |
| `account_digit` | 0.0 % | 6 | 0.0 % | 13 |  |
| `date_shifted` | 0.0 % | 2 | 0.0 % | 4 | declared invisible |
| `name_truncated` | 0.0 % | 5 | 0.0 % | 8 | declared invisible |

## Read this before the tables

* **The detector caught nothing.** Every wrong document passed. A prediction can be internally consistent and still be wrong everywhere, and arithmetic cannot see the difference.
* This is the **heuristic** half of the rule set, reported alone. Hard rules are arithmetic identities and a violation means something is genuinely wrong; heuristics have lawful exceptions. Pooling them would let a rule with known false positives borrow the precision of rules that have none.
* Localisation is reported apart from precision because it is a strictly weaker claim: a rule can be right that a document is broken and wrong about which field broke it.
