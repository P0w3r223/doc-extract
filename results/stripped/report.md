# stripped — 108 documents

| | |
|---|---|
| baseline | `stripped` |
| answered by | `stripped` |
| saw | the gold |
| corpus | `data/synthetic` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-19T11:33:10+00:00 |

## Summary

| | |
|---|---|
| documents scored | 108 of 108 (100 %) |
| produced an invoice | 108 (100 %) |
| every field right | 0 (0.0 %) |
| field instances | 6674 (support 6066, correctly absent 608) |
| detection recall | 22.8 % |
| detection precision | 100 % |
| value accuracy | 100 % |
| accuracy | 22.8 % |

## Per field

| field | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kind` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `number` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `issue_date` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `sale_date` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `currency` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `total_gross` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `payment_account` | 89 | 89 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller.name` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller.nip` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller.address` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.name` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.nip` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.address` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
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
| `header` | 737 | 737 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller` | 324 | 324 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer` | 324 | 324 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines` | 4297 | 0 | 0 | 4297 | 0 | 0.0 % | — | — | 0.0 % |
| `rate_totals` | 384 | 0 | 0 | 384 | 0 | 0.0 % | — | — | 0.0 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 366 | 152 | 0 | 214 | 0 | 41.5 % | 100 % | 100 % | 41.5 % |
| `mixed_rates` | 628 | 152 | 0 | 476 | 0 | 24.2 % | 100 % | 100 % | 24.2 % |
| `correction` | 354 | 156 | 0 | 198 | 0 | 44.1 % | 100 % | 100 % | 44.1 % |
| `advance` | 274 | 153 | 0 | 121 | 0 | 55.8 % | 100 % | 100 % | 55.8 % |
| `reverse_charge` | 394 | 154 | 0 | 240 | 0 | 39.1 % | 100 % | 100 % | 39.1 % |
| `split_payment` | 468 | 156 | 0 | 312 | 0 | 33.3 % | 100 % | 100 % | 33.3 % |
| `foreign_currency` | 473 | 152 | 0 | 321 | 0 | 32.1 % | 100 % | 100 % | 32.1 % |
| `grosz_rounding` | 666 | 156 | 0 | 510 | 0 | 23.4 % | 100 % | 100 % | 23.4 % |
| `multi_page` | 2443 | 154 | 0 | 2289 | 0 | 6.3 % | 100 % | 100 % | 6.3 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `classic` | 1961 | 459 | 0 | 1502 | 0 | 23.4 % | 100 % | 100 % | 23.4 % |
| `ledger` | 2068 | 463 | 0 | 1605 | 0 | 22.4 % | 100 % | 100 % | 22.4 % |
| `compact` | 2037 | 463 | 0 | 1574 | 0 | 22.7 % | 100 % | 100 % | 22.7 % |

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

## Injected errors

108 of 108 documents carry at least one known error.

| kind | documents |
|---|---:|

## Read this before the tables

* This baseline saw **the gold**. A number produced by something that was handed the answer is a check on the harness, not a result about extraction.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
