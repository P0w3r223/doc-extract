# pattern — 112 documents

| | |
|---|---|
| baseline | `pattern` |
| answered by | `pattern` |
| saw | the page |
| corpus | `data/attacked` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-19T10:43:11+00:00 |

## Summary

| | |
|---|---|
| documents scored | 112 of 112 (100 %) |
| produced an invoice | 112 (100 %) |
| every field right | 28 (25.0 %) |
| field instances | 7252 (support 6615, correctly absent 637) |
| detection recall | 94.8 % |
| detection precision | 100 % |
| value accuracy | 94.8 % |
| accuracy | 89.8 % |

## Per field

| field | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kind` | 112 | 112 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `number` | 112 | 112 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `issue_date` | 112 | 112 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `sale_date` | 112 | 112 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `currency` | 112 | 112 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `total_gross` | 112 | 112 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `payment_account` | 91 | 91 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller.name` | 112 | 112 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller.nip` | 112 | 112 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller.address` | 112 | 112 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.name` | 112 | 112 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.nip` | 112 | 112 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.address` | 112 | 112 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].description` | 770 | 308 | 189 | 273 | 0 | 64.5 % | 100 % | 62.0 % | 40.0 % |
| `lines[].quantity` | 770 | 700 | 70 | 0 | 0 | 100 % | 100 % | 90.9 % | 90.9 % |
| `lines[].unit_price_net` | 770 | 700 | 70 | 0 | 0 | 100 % | 100 % | 90.9 % | 90.9 % |
| `lines[].discount` | 154 | 84 | 0 | 70 | 0 | 54.5 % | 100 % | 100 % | 54.5 % |
| `lines[].net` | 770 | 770 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].vat` | 770 | 770 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].vat_rate` | 770 | 770 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `rate_totals[].net` | 203 | 203 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `rate_totals[].vat` | 203 | 203 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per group

| group | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `header` | 763 | 763 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller` | 336 | 336 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer` | 336 | 336 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines` | 4774 | 4102 | 329 | 343 | 0 | 92.8 % | 100 % | 92.6 % | 85.9 % |
| `rate_totals` | 406 | 406 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 455 | 413 | 10 | 32 | 0 | 93.0 % | 100 % | 97.6 % | 90.8 % |
| `advance` | 301 | 266 | 28 | 7 | 0 | 97.7 % | 100 % | 90.5 % | 88.4 % |
| `foreign_currency` | 609 | 525 | 56 | 28 | 0 | 95.4 % | 100 % | 90.4 % | 86.2 % |
| `mixed_rates` | 672 | 609 | 25 | 38 | 0 | 94.3 % | 100 % | 96.1 % | 90.6 % |
| `reverse_charge` | 238 | 238 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `multi_page` | 2912 | 2597 | 133 | 182 | 0 | 93.8 % | 100 % | 95.1 % | 89.2 % |
| `correction` | 476 | 392 | 56 | 28 | 0 | 94.1 % | 100 % | 87.5 % | 82.4 % |
| `split_payment` | 518 | 469 | 21 | 28 | 0 | 94.6 % | 100 % | 95.7 % | 90.5 % |
| `grosz_rounding` | 434 | 434 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `classic` | 1456 | 1246 | 119 | 91 | 0 | 93.8 % | 100 % | 91.3 % | 85.6 % |
| `compact` | 2541 | 2534 | 7 | 0 | 0 | 100 % | 100 % | 99.7 % | 99.7 % |
| `ledger` | 2618 | 2163 | 203 | 252 | 0 | 90.4 % | 100 % | 91.4 % | 82.6 % |

## Failures and stop reasons

| failure class | documents |
|---|---:|
| `none` | 112 |

| stop reason | documents |
|---|---:|
| `end_turn` | 112 |

## Cost

Over **every** attempt, including the ones that failed and were repaired.

| | |
|---|---:|
| attempts | 112 |
| of which repairs | 0 |
| input tokens | 0 |
| output tokens | 0 |
| cache write tokens | 0 |
| cache read tokens | 0 |

## Read this before the tables

* This baseline saw **the page**.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
