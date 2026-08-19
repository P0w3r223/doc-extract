# claude — 108 documents

| | |
|---|---|
| baseline | `claude` |
| answered by | `claude-haiku-4-5` |
| saw | the page |
| corpus | `data\synthetic` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-19T08:40:50+00:00 |

## Summary

| | |
|---|---|
| documents scored | 108 of 108 (100.0 %) |
| produced an invoice | 107 (99.1 %) |
| every field right | 65 (60.2 %) |
| field instances | 6674 (support 6066, correctly absent 597) |
| detection recall | 98.9 % |
| detection precision | 99.8 % |
| value accuracy | 98.9 % |
| accuracy | 97.8 % |

## Per field

| field | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kind` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100.0 % | 100.0 % | 99.1 % |
| `number` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100.0 % | 100.0 % | 99.1 % |
| `issue_date` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100.0 % | 100.0 % | 99.1 % |
| `sale_date` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100.0 % | 100.0 % | 99.1 % |
| `currency` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100.0 % | 100.0 % | 99.1 % |
| `total_gross` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100.0 % | 100.0 % | 99.1 % |
| `payment_account` | 89 | 63 | 25 | 1 | 0 | 98.9 % | 100.0 % | 71.6 % | 70.8 % |
| `seller.name` | 108 | 106 | 1 | 1 | 0 | 99.1 % | 100.0 % | 99.1 % | 98.1 % |
| `seller.nip` | 108 | 106 | 1 | 1 | 0 | 99.1 % | 100.0 % | 99.1 % | 98.1 % |
| `seller.address` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100.0 % | 100.0 % | 99.1 % |
| `buyer.name` | 108 | 106 | 1 | 1 | 0 | 99.1 % | 100.0 % | 99.1 % | 98.1 % |
| `buyer.nip` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100.0 % | 100.0 % | 99.1 % |
| `buyer.address` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100.0 % | 100.0 % | 99.1 % |
| `lines[].description` | 698 | 653 | 38 | 7 | 0 | 99.0 % | 100.0 % | 94.5 % | 93.6 % |
| `lines[].quantity` | 698 | 691 | 0 | 7 | 0 | 99.0 % | 100.0 % | 100.0 % | 99.0 % |
| `lines[].unit_price_net` | 698 | 691 | 0 | 7 | 0 | 99.0 % | 100.0 % | 100.0 % | 99.0 % |
| `lines[].discount` | 109 | 103 | 0 | 6 | 11 | 94.5 % | 90.4 % | 100.0 % | 94.5 % |
| `lines[].net` | 698 | 691 | 0 | 7 | 0 | 99.0 % | 100.0 % | 100.0 % | 99.0 % |
| `lines[].vat` | 698 | 691 | 0 | 7 | 0 | 99.0 % | 100.0 % | 100.0 % | 99.0 % |
| `lines[].vat_rate` | 698 | 691 | 0 | 7 | 0 | 99.0 % | 100.0 % | 100.0 % | 99.0 % |
| `rate_totals[].net` | 192 | 188 | 0 | 4 | 0 | 97.9 % | 100.0 % | 100.0 % | 97.9 % |
| `rate_totals[].vat` | 192 | 188 | 0 | 4 | 0 | 97.9 % | 100.0 % | 100.0 % | 97.9 % |

## Per group

| group | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `header` | 737 | 705 | 25 | 7 | 0 | 99.1 % | 100.0 % | 96.6 % | 95.7 % |
| `seller` | 324 | 319 | 2 | 3 | 0 | 99.1 % | 100.0 % | 99.4 % | 98.5 % |
| `buyer` | 324 | 320 | 1 | 3 | 0 | 99.1 % | 100.0 % | 99.7 % | 98.8 % |
| `lines` | 4297 | 4211 | 38 | 48 | 11 | 98.9 % | 99.7 % | 99.1 % | 98.0 % |
| `rate_totals` | 384 | 376 | 0 | 8 | 0 | 97.9 % | 100.0 % | 100.0 % | 97.9 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 366 | 363 | 3 | 0 | 0 | 100.0 % | 100.0 % | 99.2 % | 99.2 % |
| `mixed_rates` | 628 | 559 | 5 | 64 | 2 | 89.8 % | 99.6 % | 99.1 % | 89.0 % |
| `correction` | 354 | 352 | 2 | 0 | 5 | 100.0 % | 98.6 % | 99.4 % | 99.4 % |
| `advance` | 274 | 268 | 6 | 0 | 0 | 100.0 % | 100.0 % | 97.8 % | 97.8 % |
| `reverse_charge` | 394 | 392 | 2 | 0 | 0 | 100.0 % | 100.0 % | 99.5 % | 99.5 % |
| `split_payment` | 468 | 466 | 2 | 0 | 0 | 100.0 % | 100.0 % | 99.6 % | 99.6 % |
| `foreign_currency` | 473 | 470 | 3 | 0 | 0 | 100.0 % | 100.0 % | 99.4 % | 99.4 % |
| `grosz_rounding` | 666 | 658 | 5 | 3 | 4 | 99.5 % | 99.4 % | 99.2 % | 98.8 % |
| `multi_page` | 2443 | 2403 | 38 | 2 | 0 | 99.9 % | 100.0 % | 98.4 % | 98.4 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `classic` | 1961 | 1873 | 20 | 68 | 1 | 96.5 % | 99.9 % | 98.9 % | 95.5 % |
| `ledger` | 2068 | 2044 | 23 | 1 | 10 | 100.0 % | 99.5 % | 98.9 % | 98.8 % |
| `compact` | 2037 | 2014 | 23 | 0 | 0 | 100.0 % | 100.0 % | 98.9 % | 98.9 % |

## Failures and stop reasons

| failure class | documents |
|---|---:|
| `none` | 107 |
| `truncated` | 1 |

| stop reason | documents |
|---|---:|
| `end_turn` | 107 |
| `max_tokens` | 1 |

## Cost

Over **every** attempt, including the ones that failed and were repaired.

| | |
|---|---:|
| attempts | 109 |
| of which repairs | 1 |
| input tokens | 403577 |
| output tokens | 87138 |
| cache write tokens | 0 |
| cache read tokens | 0 |

## Read this before the tables

* This baseline saw **the page**.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
