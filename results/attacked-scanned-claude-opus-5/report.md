# claude — 168 documents

| | |
|---|---|
| baseline | `claude` |
| answered by | `claude-opus-5` |
| saw | the page |
| corpus | `data/attacked-scanned` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-20T11:36:35+00:00 |
| reads | the page as an image |

## Summary

| | |
|---|---|
| documents scored | 168 of 168 (100 %) |
| produced an invoice | 168 (100 %) |
| every field right | 126 (75.0 %) |
| field instances | 10269 (support 9366, correctly absent 903) |
| detection recall | 100 % |
| detection precision | 100 % |
| value accuracy | 99.6 % |
| accuracy | 99.6 % |

## Per field

| field | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kind` | 168 | 168 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `number` | 168 | 168 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `issue_date` | 168 | 168 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `sale_date` | 168 | 168 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `currency` | 168 | 168 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `total_gross` | 168 | 168 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `payment_account` | 126 | 126 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller.name` | 168 | 168 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller.nip` | 168 | 168 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller.address` | 168 | 168 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.name` | 168 | 168 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.nip` | 168 | 168 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.address` | 168 | 168 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].description` | 1071 | 1029 | 42 | 0 | 0 | 100 % | 100 % | 96.1 % | 96.1 % |
| `lines[].quantity` | 1071 | 1071 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].unit_price_net` | 1071 | 1071 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].discount` | 210 | 210 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].net` | 1071 | 1071 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].vat` | 1071 | 1071 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].vat_rate` | 1071 | 1071 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `rate_totals[].net` | 294 | 294 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `rate_totals[].vat` | 294 | 294 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per group

| group | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `header` | 1134 | 1134 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller` | 504 | 504 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer` | 504 | 504 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines` | 6636 | 6594 | 42 | 0 | 0 | 100 % | 100 % | 99.4 % | 99.4 % |
| `rate_totals` | 588 | 588 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 546 | 525 | 21 | 0 | 0 | 100 % | 100 % | 96.2 % | 96.2 % |
| `advance` | 441 | 420 | 21 | 0 | 0 | 100 % | 100 % | 95.2 % | 95.2 % |
| `foreign_currency` | 987 | 987 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `mixed_rates` | 945 | 945 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `reverse_charge` | 714 | 714 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `multi_page` | 4284 | 4284 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `correction` | 735 | 735 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `split_payment` | 714 | 714 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `searchable` | 3122 | 3108 | 14 | 0 | 0 | 100 % | 100 % | 99.6 % | 99.6 % |
| `rasterised` | 3122 | 3108 | 14 | 0 | 0 | 100 % | 100 % | 99.6 % | 99.6 % |
| `scanned` | 3122 | 3108 | 14 | 0 | 0 | 100 % | 100 % | 99.6 % | 99.6 % |

## Failures and stop reasons

| failure class | documents |
|---|---:|
| `none` | 168 |

| stop reason | documents |
|---|---:|
| `end_turn` | 168 |

## Cost

Over **every** attempt, including the ones that failed and were repaired.

| | |
|---|---:|
| attempts | 168 |
| of which repairs | 0 |
| input tokens | 431991 |
| output tokens | 145316 |
| cache write tokens | 0 |
| cache read tokens | 573384 |

## Read this before the tables

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* This baseline saw **the page**.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
