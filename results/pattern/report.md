# pattern — 108 documents

| | |
|---|---|
| baseline | `pattern` |
| answered by | `pattern` |
| saw | the page |
| corpus | `data/synthetic` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 8192, repair 4096, at most 1 repair(s) |
| started | 2026-08-18T16:05:32+00:00 |

## Summary

| | |
|---|---|
| documents scored | 108 of 108 (100 %) |
| produced an invoice | 104 (96.3 %) |
| every field right | 35 (32.4 %) |
| field instances | 6674 (support 6066, correctly absent 608) |
| detection recall | 91.1 % |
| detection precision | 100 % |
| value accuracy | 94.7 % |
| accuracy | 86.3 % |

## Per field

| field | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kind` | 108 | 104 | 0 | 4 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `number` | 108 | 104 | 0 | 4 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `issue_date` | 108 | 104 | 0 | 4 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `sale_date` | 108 | 104 | 0 | 4 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `currency` | 108 | 104 | 0 | 4 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `total_gross` | 108 | 104 | 0 | 4 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `payment_account` | 89 | 85 | 0 | 4 | 0 | 95.5 % | 100 % | 100 % | 95.5 % |
| `seller.name` | 108 | 104 | 0 | 4 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `seller.nip` | 108 | 104 | 0 | 4 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `seller.address` | 108 | 104 | 0 | 4 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `buyer.name` | 108 | 104 | 0 | 4 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `buyer.nip` | 108 | 104 | 0 | 4 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `buyer.address` | 108 | 104 | 0 | 4 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `lines[].description` | 698 | 232 | 181 | 285 | 0 | 59.2 % | 100 % | 56.2 % | 33.2 % |
| `lines[].quantity` | 698 | 617 | 56 | 25 | 0 | 96.4 % | 100 % | 91.7 % | 88.4 % |
| `lines[].unit_price_net` | 698 | 618 | 55 | 25 | 0 | 96.4 % | 100 % | 91.8 % | 88.5 % |
| `lines[].discount` | 109 | 47 | 0 | 62 | 0 | 43.1 % | 100 % | 100 % | 43.1 % |
| `lines[].net` | 698 | 673 | 0 | 25 | 0 | 96.4 % | 100 % | 100 % | 96.4 % |
| `lines[].vat` | 698 | 673 | 0 | 25 | 0 | 96.4 % | 100 % | 100 % | 96.4 % |
| `lines[].vat_rate` | 698 | 673 | 0 | 25 | 0 | 96.4 % | 100 % | 100 % | 96.4 % |
| `rate_totals[].net` | 192 | 184 | 0 | 8 | 0 | 95.8 % | 100 % | 100 % | 95.8 % |
| `rate_totals[].vat` | 192 | 184 | 0 | 8 | 0 | 95.8 % | 100 % | 100 % | 95.8 % |

## Per group

| group | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `header` | 737 | 709 | 0 | 28 | 0 | 96.2 % | 100 % | 100 % | 96.2 % |
| `seller` | 324 | 312 | 0 | 12 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `buyer` | 324 | 312 | 0 | 12 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `lines` | 4297 | 3533 | 292 | 472 | 0 | 89.0 % | 100 % | 92.4 % | 82.2 % |
| `rate_totals` | 384 | 368 | 0 | 16 | 0 | 95.8 % | 100 % | 100 % | 95.8 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 366 | 342 | 7 | 17 | 0 | 95.4 % | 100 % | 98.0 % | 93.4 % |
| `mixed_rates` | 628 | 576 | 22 | 30 | 0 | 95.2 % | 100 % | 96.3 % | 91.7 % |
| `correction` | 354 | 313 | 23 | 18 | 0 | 94.9 % | 100 % | 93.2 % | 88.4 % |
| `advance` | 274 | 261 | 6 | 7 | 0 | 97.4 % | 100 % | 97.8 % | 95.3 % |
| `reverse_charge` | 394 | 357 | 32 | 5 | 0 | 98.7 % | 100 % | 91.8 % | 90.6 % |
| `split_payment` | 468 | 422 | 20 | 26 | 0 | 94.4 % | 100 % | 95.5 % | 90.2 % |
| `foreign_currency` | 473 | 440 | 20 | 13 | 0 | 97.3 % | 100 % | 95.7 % | 93.0 % |
| `grosz_rounding` | 666 | 418 | 10 | 238 | 0 | 64.3 % | 100 % | 97.7 % | 62.8 % |
| `multi_page` | 2443 | 2105 | 152 | 186 | 0 | 92.4 % | 100 % | 93.3 % | 86.2 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `classic` | 1961 | 1563 | 156 | 242 | 0 | 87.7 % | 100 % | 90.9 % | 79.7 % |
| `ledger` | 2068 | 1641 | 136 | 291 | 0 | 85.9 % | 100 % | 92.3 % | 79.4 % |
| `compact` | 2037 | 2030 | 0 | 7 | 0 | 99.7 % | 100 % | 100 % | 99.7 % |

## Failures and stop reasons

| failure class | documents |
|---|---:|
| `none` | 104 |
| `schema_invalid` | 4 |

| stop reason | documents |
|---|---:|
| `end_turn` | 108 |

## Cost

Over **every** attempt, including the ones that failed and were repaired.

| | |
|---|---:|
| attempts | 112 |
| of which repairs | 4 |
| input tokens | 0 |
| output tokens | 0 |
| cache write tokens | 0 |
| cache read tokens | 0 |

## Read this before the tables

* This baseline saw **the page**.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
