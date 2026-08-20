# oracle — 168 documents

| | |
|---|---|
| baseline | `oracle` |
| answered by | `oracle` |
| saw | the gold |
| corpus | `data/attacked-scanned` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-20T10:46:19+00:00 |

## Summary

| | |
|---|---|
| documents scored | 168 of 168 (100 %) |
| produced an invoice | 168 (100 %) |
| every field right | 168 (100 %) |
| field instances | 10269 (support 9366, correctly absent 903) |
| detection recall | 100 % |
| detection precision | 100 % |
| value accuracy | 100 % |
| accuracy | 100 % |

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
| `lines[].description` | 1071 | 1071 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
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
| `lines` | 6636 | 6636 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `rate_totals` | 588 | 588 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 546 | 546 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `advance` | 441 | 441 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `foreign_currency` | 987 | 987 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `mixed_rates` | 945 | 945 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `reverse_charge` | 714 | 714 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `multi_page` | 4284 | 4284 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `correction` | 735 | 735 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `split_payment` | 714 | 714 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `searchable` | 3122 | 3122 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `rasterised` | 3122 | 3122 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `scanned` | 3122 | 3122 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

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
| input tokens | 0 |
| output tokens | 0 |
| cache write tokens | 0 |
| cache read tokens | 0 |

## Read this before the tables

* This baseline saw **the gold**. A number produced by something that was handed the answer is a check on the harness, not a result about extraction.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
