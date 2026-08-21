# pattern — 168 documents

| | |
|---|---|
| baseline | `pattern` |
| answered by | `pattern` |
| saw | the page |
| corpus | `data/attacked-scanned` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-20T10:46:26+00:00 |

## Summary

| | |
|---|---|
| documents scored | 168 of 168 (100 %) |
| produced an invoice | 56 (33.3 %) |
| every field right | 14 (8.3 %) |
| field instances | 10269 (support 9366, correctly absent 903) |
| detection recall | 30.6 % |
| detection precision | 100 % |
| value accuracy | 92.0 % |
| accuracy | 28.2 % |

## Per field

| field | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kind` | 168 | 56 | 0 | 112 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `number` | 168 | 56 | 0 | 112 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `issue_date` | 168 | 56 | 0 | 112 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `sale_date` | 168 | 56 | 0 | 112 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `currency` | 168 | 56 | 0 | 112 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `total_gross` | 168 | 56 | 0 | 112 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `payment_account` | 126 | 42 | 0 | 84 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `seller.name` | 168 | 56 | 0 | 112 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `seller.nip` | 168 | 56 | 0 | 112 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `seller.address` | 168 | 56 | 0 | 112 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `buyer.name` | 168 | 56 | 0 | 112 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `buyer.nip` | 168 | 56 | 0 | 112 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `buyer.address` | 168 | 56 | 0 | 112 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `lines[].description` | 1071 | 42 | 116 | 913 | 0 | 14.8 % | 100 % | 26.6 % | 3.9 % |
| `lines[].quantity` | 1071 | 301 | 56 | 714 | 0 | 33.3 % | 100 % | 84.3 % | 28.1 % |
| `lines[].unit_price_net` | 1071 | 301 | 56 | 714 | 0 | 33.3 % | 100 % | 84.3 % | 28.1 % |
| `lines[].discount` | 210 | 14 | 0 | 196 | 0 | 6.7 % | 100 % | 100 % | 6.7 % |
| `lines[].net` | 1071 | 357 | 0 | 714 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `lines[].vat` | 1071 | 357 | 0 | 714 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `lines[].vat_rate` | 1071 | 357 | 0 | 714 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `rate_totals[].net` | 294 | 98 | 0 | 196 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `rate_totals[].vat` | 294 | 98 | 0 | 196 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |

## Per group

| group | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `header` | 1134 | 378 | 0 | 756 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `seller` | 504 | 168 | 0 | 336 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `buyer` | 504 | 168 | 0 | 336 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `lines` | 6636 | 1729 | 228 | 4679 | 0 | 29.5 % | 100 % | 88.3 % | 26.1 % |
| `rate_totals` | 588 | 196 | 0 | 392 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 546 | 168 | 4 | 374 | 0 | 31.5 % | 100 % | 97.7 % | 30.8 % |
| `advance` | 441 | 140 | 7 | 294 | 0 | 33.3 % | 100 % | 95.2 % | 31.7 % |
| `foreign_currency` | 987 | 273 | 35 | 679 | 0 | 31.2 % | 100 % | 88.6 % | 27.7 % |
| `mixed_rates` | 945 | 287 | 7 | 651 | 0 | 31.1 % | 100 % | 97.6 % | 30.4 % |
| `reverse_charge` | 714 | 238 | 0 | 476 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `multi_page` | 4284 | 1113 | 133 | 3038 | 0 | 29.1 % | 100 % | 89.3 % | 26.0 % |
| `correction` | 735 | 182 | 42 | 511 | 0 | 30.5 % | 100 % | 81.2 % | 24.8 % |
| `split_payment` | 714 | 238 | 0 | 476 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `searchable` | 3122 | 2639 | 228 | 255 | 0 | 91.8 % | 100 % | 92.0 % | 84.5 % |
| `rasterised` | 3122 | 0 | 0 | 3122 | 0 | 0.0 % | — | — | 0.0 % |
| `scanned` | 3122 | 0 | 0 | 3122 | 0 | 0.0 % | — | — | 0.0 % |

## Failures and stop reasons

| failure class | documents |
|---|---:|
| `schema_invalid` | 112 |
| `none` | 56 |

| stop reason | documents |
|---|---:|
| `end_turn` | 168 |

## Cost

Over **every** attempt, including the ones that failed and were repaired.

| | |
|---|---:|
| attempts | 280 |
| of which repairs | 112 |
| input tokens | 0 |
| output tokens | 0 |
| cache write tokens | 0 |
| cache read tokens | 0 |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* This baseline saw **the page**.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
