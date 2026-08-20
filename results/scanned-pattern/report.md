# pattern — 108 documents

| | |
|---|---|
| baseline | `pattern` |
| answered by | `pattern` |
| saw | the page |
| corpus | `data/scanned` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-20T08:37:37+00:00 |

## Summary

| | |
|---|---|
| documents scored | 108 of 108 (100 %) |
| produced an invoice | 34 (31.5 %) |
| every field right | 0 (0.0 %) |
| field instances | 6674 (support 6066, correctly absent 608) |
| detection recall | 28.3 % |
| detection precision | 100 % |
| value accuracy | 90.9 % |
| accuracy | 25.8 % |

## Per field

| field | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kind` | 108 | 34 | 0 | 74 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `number` | 108 | 34 | 0 | 74 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `issue_date` | 108 | 34 | 0 | 74 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `sale_date` | 108 | 34 | 0 | 74 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `currency` | 108 | 34 | 0 | 74 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `total_gross` | 108 | 34 | 0 | 74 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `payment_account` | 89 | 25 | 0 | 64 | 0 | 28.1 % | 100 % | 100 % | 28.1 % |
| `seller.name` | 108 | 34 | 0 | 74 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `seller.nip` | 108 | 34 | 0 | 74 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `seller.address` | 108 | 34 | 0 | 74 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `buyer.name` | 108 | 34 | 0 | 74 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `buyer.nip` | 108 | 34 | 0 | 74 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `buyer.address` | 108 | 34 | 0 | 74 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `lines[].description` | 698 | 0 | 101 | 597 | 0 | 14.5 % | 100 % | 0.0 % | 0.0 % |
| `lines[].quantity` | 698 | 185 | 28 | 485 | 0 | 30.5 % | 100 % | 86.9 % | 26.5 % |
| `lines[].unit_price_net` | 698 | 186 | 27 | 485 | 0 | 30.5 % | 100 % | 87.3 % | 26.6 % |
| `lines[].discount` | 109 | 0 | 0 | 109 | 0 | 0.0 % | — | — | 0.0 % |
| `lines[].net` | 698 | 213 | 0 | 485 | 0 | 30.5 % | 100 % | 100 % | 30.5 % |
| `lines[].vat` | 698 | 213 | 0 | 485 | 0 | 30.5 % | 100 % | 100 % | 30.5 % |
| `lines[].vat_rate` | 698 | 213 | 0 | 485 | 0 | 30.5 % | 100 % | 100 % | 30.5 % |
| `rate_totals[].net` | 192 | 60 | 0 | 132 | 0 | 31.2 % | 100 % | 100 % | 31.2 % |
| `rate_totals[].vat` | 192 | 60 | 0 | 132 | 0 | 31.2 % | 100 % | 100 % | 31.2 % |

## Per group

| group | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `header` | 737 | 229 | 0 | 508 | 0 | 31.1 % | 100 % | 100 % | 31.1 % |
| `seller` | 324 | 102 | 0 | 222 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `buyer` | 324 | 102 | 0 | 222 | 0 | 31.5 % | 100 % | 100 % | 31.5 % |
| `lines` | 4297 | 1010 | 156 | 3131 | 0 | 27.1 % | 100 % | 86.6 % | 23.5 % |
| `rate_totals` | 384 | 120 | 0 | 264 | 0 | 31.2 % | 100 % | 100 % | 31.2 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 366 | 100 | 5 | 261 | 0 | 28.7 % | 100 % | 95.2 % | 27.3 % |
| `mixed_rates` | 628 | 181 | 10 | 437 | 0 | 30.4 % | 100 % | 94.8 % | 28.8 % |
| `correction` | 354 | 99 | 13 | 242 | 0 | 31.6 % | 100 % | 88.4 % | 28.0 % |
| `advance` | 274 | 82 | 5 | 187 | 0 | 31.8 % | 100 % | 94.3 % | 29.9 % |
| `reverse_charge` | 394 | 107 | 17 | 270 | 0 | 31.5 % | 100 % | 86.3 % | 27.2 % |
| `split_payment` | 468 | 141 | 11 | 316 | 0 | 32.5 % | 100 % | 92.8 % | 30.1 % |
| `foreign_currency` | 473 | 142 | 10 | 321 | 0 | 32.1 % | 100 % | 93.4 % | 30.0 % |
| `grosz_rounding` | 666 | 94 | 4 | 568 | 0 | 14.7 % | 100 % | 95.9 % | 14.1 % |
| `multi_page` | 2443 | 617 | 81 | 1745 | 0 | 28.6 % | 100 % | 88.4 % | 25.3 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `searchable` | 1961 | 1563 | 156 | 242 | 0 | 87.7 % | 100 % | 90.9 % | 79.7 % |
| `rasterised` | 2068 | 0 | 0 | 2068 | 0 | 0.0 % | — | — | 0.0 % |
| `scanned` | 2037 | 0 | 0 | 2037 | 0 | 0.0 % | — | — | 0.0 % |

## Failures and stop reasons

| failure class | documents |
|---|---:|
| `schema_invalid` | 74 |
| `none` | 34 |

| stop reason | documents |
|---|---:|
| `end_turn` | 108 |

## Cost

Over **every** attempt, including the ones that failed and were repaired.

| | |
|---|---:|
| attempts | 182 |
| of which repairs | 74 |
| input tokens | 0 |
| output tokens | 0 |
| cache write tokens | 0 |
| cache read tokens | 0 |

## Read this before the tables

* This baseline saw **the page**.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
