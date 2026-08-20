# claude — 108 documents

| | |
|---|---|
| baseline | `claude` |
| answered by | `claude-haiku-4-5` |
| saw | the page |
| corpus | `data/scanned` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-20T09:03:18+00:00 |
| reads | the page as an image |

## Summary

| | |
|---|---|
| documents scored | 108 of 108 (100 %) |
| produced an invoice | 107 (99.1 %) |
| every field right | 10 (9.3 %) |
| field instances | 6696 (support 6066, correctly absent 607) |
| detection recall | 96.4 % |
| detection precision | 99.6 % |
| value accuracy | 92.1 % |
| accuracy | 88.7 % |

## Per field

| field | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kind` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100 % | 100 % | 99.1 % |
| `number` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100 % | 100 % | 99.1 % |
| `issue_date` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100 % | 100 % | 99.1 % |
| `sale_date` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100 % | 100 % | 99.1 % |
| `currency` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100 % | 100 % | 99.1 % |
| `total_gross` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100 % | 100 % | 99.1 % |
| `payment_account` | 89 | 30 | 58 | 1 | 0 | 98.9 % | 100 % | 34.1 % | 33.7 % |
| `seller.name` | 108 | 86 | 21 | 1 | 0 | 99.1 % | 100 % | 80.4 % | 79.6 % |
| `seller.nip` | 108 | 106 | 1 | 1 | 0 | 99.1 % | 100 % | 99.1 % | 98.1 % |
| `seller.address` | 108 | 106 | 1 | 1 | 0 | 99.1 % | 100 % | 99.1 % | 98.1 % |
| `buyer.name` | 108 | 104 | 3 | 1 | 0 | 99.1 % | 100 % | 97.2 % | 96.3 % |
| `buyer.nip` | 108 | 107 | 0 | 1 | 0 | 99.1 % | 100 % | 100 % | 99.1 % |
| `buyer.address` | 108 | 102 | 5 | 1 | 0 | 99.1 % | 100 % | 95.3 % | 94.4 % |
| `lines[].description` | 698 | 335 | 337 | 26 | 0 | 96.3 % | 100 % | 49.9 % | 48.0 % |
| `lines[].quantity` | 698 | 672 | 0 | 26 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `lines[].unit_price_net` | 698 | 653 | 3 | 42 | 0 | 94.0 % | 100 % | 99.5 % | 93.6 % |
| `lines[].discount` | 109 | 101 | 0 | 8 | 1 | 92.7 % | 99.0 % | 100 % | 92.7 % |
| `lines[].net` | 698 | 672 | 0 | 26 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `lines[].vat` | 698 | 672 | 0 | 26 | 0 | 96.3 % | 100 % | 100 % | 96.3 % |
| `lines[].vat_rate` | 698 | 639 | 33 | 26 | 0 | 96.3 % | 100 % | 95.1 % | 91.5 % |
| `rate_totals[].net` | 192 | 178 | 0 | 14 | 11 | 92.7 % | 94.2 % | 100 % | 92.7 % |
| `rate_totals[].vat` | 192 | 178 | 0 | 14 | 11 | 92.7 % | 94.2 % | 100 % | 92.7 % |

## Per group

| group | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `header` | 737 | 672 | 58 | 7 | 0 | 99.1 % | 100 % | 92.1 % | 91.2 % |
| `seller` | 324 | 298 | 23 | 3 | 0 | 99.1 % | 100 % | 92.8 % | 92.0 % |
| `buyer` | 324 | 313 | 8 | 3 | 0 | 99.1 % | 100 % | 97.5 % | 96.6 % |
| `lines` | 4297 | 3744 | 373 | 180 | 1 | 95.8 % | 99.98 % | 90.9 % | 87.1 % |
| `rate_totals` | 384 | 356 | 0 | 28 | 22 | 92.7 % | 94.2 % | 100 % | 92.7 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 366 | 344 | 21 | 1 | 0 | 99.7 % | 100 % | 94.2 % | 94.0 % |
| `mixed_rates` | 628 | 593 | 34 | 1 | 0 | 99.8 % | 100 % | 94.6 % | 94.4 % |
| `correction` | 354 | 341 | 13 | 0 | 0 | 100 % | 100 % | 96.3 % | 96.3 % |
| `advance` | 274 | 258 | 16 | 0 | 0 | 100 % | 100 % | 94.2 % | 94.2 % |
| `reverse_charge` | 394 | 315 | 57 | 22 | 23 | 94.4 % | 94.2 % | 84.7 % | 79.9 % |
| `split_payment` | 468 | 439 | 29 | 0 | 0 | 100 % | 100 % | 93.8 % | 93.8 % |
| `foreign_currency` | 473 | 444 | 29 | 0 | 0 | 100 % | 100 % | 93.9 % | 93.9 % |
| `grosz_rounding` | 666 | 585 | 64 | 17 | 0 | 97.4 % | 100 % | 90.1 % | 87.8 % |
| `multi_page` | 2443 | 2064 | 199 | 180 | 0 | 92.6 % | 100 % | 91.2 % | 84.5 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `searchable` | 1961 | 1805 | 148 | 8 | 8 | 99.6 % | 99.6 % | 92.4 % | 92.0 % |
| `rasterised` | 2068 | 1713 | 169 | 186 | 7 | 91.0 % | 99.6 % | 91.0 % | 82.8 % |
| `scanned` | 2037 | 1865 | 145 | 27 | 8 | 98.7 % | 99.6 % | 92.8 % | 91.6 % |

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
| input tokens | 510085 |
| output tokens | 90514 |
| cache write tokens | 0 |
| cache read tokens | 0 |

## Read this before the tables

* This baseline saw **the page**.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
