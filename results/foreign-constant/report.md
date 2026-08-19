# constant — 108 documents

| | |
|---|---|
| baseline | `constant` |
| answered by | `constant` |
| saw | nothing |
| corpus | `data/foreign` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-19T11:56:33+00:00 |

## Summary

| | |
|---|---|
| documents scored | 108 of 108 (100 %) |
| produced an invoice | 108 (100 %) |
| every field right | 0 (0.0 %) |
| field instances | 6674 (support 6066, correctly absent 608) |
| detection recall | 12.5 % |
| detection precision | 100 % |
| value accuracy | 23.8 % |
| accuracy | 3.0 % |

## Per field

| field | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kind` | 108 | 84 | 24 | 0 | 0 | 100 % | 100 % | 77.8 % | 77.8 % |
| `number` | 108 | 0 | 108 | 0 | 0 | 100 % | 100 % | 0.0 % | 0.0 % |
| `issue_date` | 108 | 0 | 108 | 0 | 0 | 100 % | 100 % | 0.0 % | 0.0 % |
| `sale_date` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `currency` | 108 | 96 | 12 | 0 | 0 | 100 % | 100 % | 88.9 % | 88.9 % |
| `total_gross` | 108 | 0 | 108 | 0 | 0 | 100 % | 100 % | 0.0 % | 0.0 % |
| `payment_account` | 89 | 0 | 0 | 89 | 0 | 0.0 % | — | — | 0.0 % |
| `seller.name` | 108 | 0 | 108 | 0 | 0 | 100 % | 100 % | 0.0 % | 0.0 % |
| `seller.nip` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `seller.address` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `buyer.name` | 108 | 0 | 108 | 0 | 0 | 100 % | 100 % | 0.0 % | 0.0 % |
| `buyer.nip` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `buyer.address` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `lines[].description` | 698 | 0 | 0 | 698 | 0 | 0.0 % | — | — | 0.0 % |
| `lines[].quantity` | 698 | 0 | 0 | 698 | 0 | 0.0 % | — | — | 0.0 % |
| `lines[].unit_price_net` | 698 | 0 | 0 | 698 | 0 | 0.0 % | — | — | 0.0 % |
| `lines[].discount` | 109 | 0 | 0 | 109 | 0 | 0.0 % | — | — | 0.0 % |
| `lines[].net` | 698 | 0 | 0 | 698 | 0 | 0.0 % | — | — | 0.0 % |
| `lines[].vat` | 698 | 0 | 0 | 698 | 0 | 0.0 % | — | — | 0.0 % |
| `lines[].vat_rate` | 698 | 0 | 0 | 698 | 0 | 0.0 % | — | — | 0.0 % |
| `rate_totals[].net` | 192 | 0 | 0 | 192 | 0 | 0.0 % | — | — | 0.0 % |
| `rate_totals[].vat` | 192 | 0 | 0 | 192 | 0 | 0.0 % | — | — | 0.0 % |

## Per group

| group | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `header` | 737 | 180 | 360 | 197 | 0 | 73.3 % | 100 % | 33.3 % | 24.4 % |
| `seller` | 324 | 0 | 108 | 216 | 0 | 33.3 % | 100 % | 0.0 % | 0.0 % |
| `buyer` | 324 | 0 | 108 | 216 | 0 | 33.3 % | 100 % | 0.0 % | 0.0 % |
| `lines` | 4297 | 0 | 0 | 4297 | 0 | 0.0 % | — | — | 0.0 % |
| `rate_totals` | 384 | 0 | 0 | 384 | 0 | 0.0 % | — | — | 0.0 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 366 | 24 | 60 | 282 | 0 | 23.0 % | 100 % | 28.6 % | 6.6 % |
| `mixed_rates` | 628 | 24 | 60 | 544 | 0 | 13.4 % | 100 % | 28.6 % | 3.8 % |
| `correction` | 354 | 12 | 72 | 270 | 0 | 23.7 % | 100 % | 14.3 % | 3.4 % |
| `advance` | 274 | 12 | 72 | 190 | 0 | 30.7 % | 100 % | 14.3 % | 4.4 % |
| `reverse_charge` | 394 | 24 | 60 | 310 | 0 | 21.3 % | 100 % | 28.6 % | 6.1 % |
| `split_payment` | 468 | 24 | 60 | 384 | 0 | 17.9 % | 100 % | 28.6 % | 5.1 % |
| `foreign_currency` | 473 | 12 | 72 | 389 | 0 | 17.8 % | 100 % | 14.3 % | 2.5 % |
| `grosz_rounding` | 666 | 24 | 60 | 582 | 0 | 12.6 % | 100 % | 28.6 % | 3.6 % |
| `multi_page` | 2443 | 24 | 60 | 2359 | 0 | 3.4 % | 100 % | 28.6 % | 1.0 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `letterhead` | 1961 | 60 | 192 | 1709 | 0 | 12.9 % | 100 % | 23.8 % | 3.1 % |
| `statement` | 2068 | 60 | 192 | 1816 | 0 | 12.2 % | 100 % | 23.8 % | 2.9 % |
| `slip` | 2037 | 60 | 192 | 1785 | 0 | 12.4 % | 100 % | 23.8 % | 2.9 % |

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
| attempts | 108 |
| of which repairs | 0 |
| input tokens | 0 |
| output tokens | 0 |
| cache write tokens | 0 |
| cache read tokens | 0 |

## Read this before the tables

* This baseline saw **nothing**.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
