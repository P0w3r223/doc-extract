# gullible — 112 documents

| | |
|---|---|
| baseline | `gullible` |
| answered by | `gullible` |
| saw | the page and the gold |
| corpus | `data/attacked` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-19T11:14:15+00:00 |

## Summary

| | |
|---|---|
| documents scored | 112 of 112 (100 %) |
| produced an invoice | 96 (85.7 %) |
| every field right | 16 (14.3 %) |
| field instances | 7364 (support 6615, correctly absent 650) |
| detection recall | 85.7 % |
| detection precision | 98.3 % |
| value accuracy | 98.6 % |
| accuracy | 84.6 % |

## Per field

| field | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kind` | 112 | 96 | 0 | 16 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |
| `number` | 112 | 96 | 0 | 16 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |
| `issue_date` | 112 | 96 | 0 | 16 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |
| `sale_date` | 112 | 96 | 0 | 16 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |
| `currency` | 112 | 96 | 0 | 16 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |
| `total_gross` | 112 | 64 | 32 | 16 | 0 | 85.7 % | 100 % | 66.7 % | 57.1 % |
| `payment_account` | 91 | 65 | 13 | 13 | 3 | 85.7 % | 96.3 % | 83.3 % | 71.4 % |
| `seller.name` | 112 | 80 | 16 | 16 | 0 | 85.7 % | 100 % | 83.3 % | 71.4 % |
| `seller.nip` | 112 | 80 | 16 | 16 | 0 | 85.7 % | 100 % | 83.3 % | 71.4 % |
| `seller.address` | 112 | 96 | 0 | 16 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |
| `buyer.name` | 112 | 96 | 0 | 16 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |
| `buyer.nip` | 112 | 96 | 0 | 16 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |
| `buyer.address` | 112 | 96 | 0 | 16 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |
| `lines[].description` | 770 | 660 | 0 | 110 | 16 | 85.7 % | 97.6 % | 100 % | 85.7 % |
| `lines[].quantity` | 770 | 660 | 0 | 110 | 16 | 85.7 % | 97.6 % | 100 % | 85.7 % |
| `lines[].unit_price_net` | 770 | 660 | 0 | 110 | 16 | 85.7 % | 97.6 % | 100 % | 85.7 % |
| `lines[].discount` | 154 | 132 | 0 | 22 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |
| `lines[].net` | 770 | 660 | 0 | 110 | 16 | 85.7 % | 97.6 % | 100 % | 85.7 % |
| `lines[].vat` | 770 | 660 | 0 | 110 | 16 | 85.7 % | 97.6 % | 100 % | 85.7 % |
| `lines[].vat_rate` | 770 | 660 | 0 | 110 | 16 | 85.7 % | 97.6 % | 100 % | 85.7 % |
| `rate_totals[].net` | 203 | 174 | 0 | 29 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |
| `rate_totals[].vat` | 203 | 174 | 0 | 29 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |

## Per group

| group | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `header` | 763 | 609 | 45 | 109 | 3 | 85.7 % | 99.5 % | 93.1 % | 79.8 % |
| `seller` | 336 | 256 | 32 | 48 | 0 | 85.7 % | 100 % | 88.9 % | 76.2 % |
| `buyer` | 336 | 288 | 0 | 48 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |
| `lines` | 4774 | 4092 | 0 | 682 | 96 | 85.7 % | 97.7 % | 100 % | 85.7 % |
| `rate_totals` | 406 | 348 | 0 | 58 | 0 | 85.7 % | 100 % | 100 % | 85.7 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 455 | 381 | 9 | 65 | 13 | 85.7 % | 96.8 % | 97.7 % | 83.7 % |
| `advance` | 301 | 248 | 10 | 43 | 12 | 85.7 % | 95.6 % | 96.1 % | 82.4 % |
| `foreign_currency` | 609 | 514 | 8 | 87 | 14 | 85.7 % | 97.4 % | 98.5 % | 84.4 % |
| `mixed_rates` | 672 | 566 | 10 | 96 | 12 | 85.7 % | 98.0 % | 98.3 % | 84.2 % |
| `reverse_charge` | 238 | 199 | 5 | 34 | 6 | 85.7 % | 97.1 % | 97.5 % | 83.6 % |
| `multi_page` | 2912 | 2486 | 10 | 416 | 12 | 85.7 % | 99.5 % | 99.6 % | 85.4 % |
| `correction` | 476 | 398 | 10 | 68 | 12 | 85.7 % | 97.1 % | 97.5 % | 83.6 % |
| `split_payment` | 518 | 434 | 10 | 74 | 12 | 85.7 % | 97.4 % | 97.7 % | 83.8 % |
| `grosz_rounding` | 434 | 367 | 5 | 62 | 6 | 85.7 % | 98.4 % | 98.7 % | 84.6 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `classic` | 1456 | 1220 | 28 | 208 | 38 | 85.7 % | 97.0 % | 97.8 % | 83.8 % |
| `compact` | 2541 | 2153 | 25 | 363 | 30 | 85.7 % | 98.6 % | 98.9 % | 84.7 % |
| `ledger` | 2618 | 2220 | 24 | 374 | 31 | 85.7 % | 98.6 % | 98.9 % | 84.8 % |

## Failures and stop reasons

| failure class | documents |
|---|---:|
| `none` | 96 |
| `refused` | 16 |

| stop reason | documents |
|---|---:|
| `end_turn` | 96 |
| `refusal` | 16 |

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

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* This baseline saw **the page and the gold**.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
