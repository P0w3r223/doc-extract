# claude — 108 documents

| | |
|---|---|
| baseline | `claude` |
| answered by | `claude-haiku-4-5` |
| saw | the page |
| corpus | `data/foreign` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-21T09:40:02+00:00 |

## Summary

| | |
|---|---|
| documents scored | 108 of 108 (100 %) |
| produced an invoice | 108 (100 %) |
| every field right | 52 (48.1 %) |
| field instances | 6674 (support 6066, correctly absent 550) |
| detection recall | 99.5 % |
| detection precision | 99.0 % |
| value accuracy | 98.6 % |
| accuracy | 98.1 % |

## Per field

| field | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kind` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `number` | 108 | 106 | 2 | 0 | 0 | 100 % | 100 % | 98.1 % | 98.1 % |
| `issue_date` | 108 | 98 | 10 | 0 | 0 | 100 % | 100 % | 90.7 % | 90.7 % |
| `sale_date` | 108 | 95 | 13 | 0 | 0 | 100 % | 100 % | 88.0 % | 88.0 % |
| `currency` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `total_gross` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `payment_account` | 89 | 78 | 11 | 0 | 0 | 100 % | 100 % | 87.6 % | 87.6 % |
| `seller.name` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller.nip` | 108 | 107 | 1 | 0 | 0 | 100 % | 100 % | 99.1 % | 99.1 % |
| `seller.address` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.name` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.nip` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.address` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].description` | 698 | 659 | 39 | 0 | 0 | 100 % | 100 % | 94.4 % | 94.4 % |
| `lines[].quantity` | 698 | 697 | 0 | 1 | 0 | 99.9 % | 100 % | 100 % | 99.9 % |
| `lines[].unit_price_net` | 698 | 698 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].discount` | 109 | 108 | 0 | 1 | 58 | 99.1 % | 65.1 % | 100 % | 99.1 % |
| `lines[].net` | 698 | 668 | 6 | 24 | 0 | 96.6 % | 100 % | 99.1 % | 95.7 % |
| `lines[].vat` | 698 | 693 | 1 | 4 | 0 | 99.4 % | 100 % | 99.9 % | 99.3 % |
| `lines[].vat_rate` | 698 | 698 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `rate_totals[].net` | 192 | 192 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `rate_totals[].vat` | 192 | 192 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per group

| group | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `header` | 737 | 701 | 36 | 0 | 0 | 100 % | 100 % | 95.1 % | 95.1 % |
| `seller` | 324 | 323 | 1 | 0 | 0 | 100 % | 100 % | 99.7 % | 99.7 % |
| `buyer` | 324 | 324 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines` | 4297 | 4221 | 46 | 30 | 58 | 99.3 % | 98.7 % | 98.9 % | 98.2 % |
| `rate_totals` | 384 | 384 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 366 | 362 | 3 | 1 | 2 | 99.7 % | 99.5 % | 99.2 % | 98.9 % |
| `mixed_rates` | 628 | 616 | 10 | 2 | 4 | 99.7 % | 99.4 % | 98.4 % | 98.1 % |
| `correction` | 354 | 346 | 7 | 1 | 13 | 99.7 % | 96.4 % | 98.0 % | 97.7 % |
| `advance` | 274 | 273 | 0 | 1 | 1 | 99.6 % | 99.6 % | 100 % | 99.6 % |
| `reverse_charge` | 394 | 390 | 4 | 0 | 2 | 100 % | 99.5 % | 99.0 % | 99.0 % |
| `split_payment` | 468 | 460 | 8 | 0 | 1 | 100 % | 99.8 % | 98.3 % | 98.3 % |
| `foreign_currency` | 473 | 461 | 9 | 3 | 6 | 99.4 % | 98.7 % | 98.1 % | 97.5 % |
| `grosz_rounding` | 666 | 645 | 1 | 20 | 24 | 97.0 % | 96.4 % | 99.8 % | 96.8 % |
| `multi_page` | 2443 | 2400 | 41 | 2 | 5 | 99.9 % | 99.8 % | 98.3 % | 98.2 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `letterhead` | 1961 | 1937 | 20 | 4 | 20 | 99.8 % | 99.0 % | 99.0 % | 98.8 % |
| `statement` | 2068 | 2023 | 19 | 26 | 38 | 98.7 % | 98.2 % | 99.1 % | 97.8 % |
| `slip` | 2037 | 1993 | 44 | 0 | 0 | 100 % | 100 % | 97.8 % | 97.8 % |

## Failures and stop reasons

| failure class | documents |
|---|---:|
| `none` | 108 |

| stop reason | documents |
|---|---:|
| `end_turn` | 108 |

## Cost

Over **every** attempt, including the ones that failed and were repaired.

| | |
|---|---:|
| attempts | 115 |
| of which repairs | 7 |
| input tokens | 423714 |
| output tokens | 74594 |
| cache write tokens | 0 |
| cache read tokens | 0 |

## Read this before the tables

* This baseline saw **the page**.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
