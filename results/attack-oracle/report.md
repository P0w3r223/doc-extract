# oracle — 112 documents

| | |
|---|---|
| baseline | `oracle` |
| answered by | `oracle` |
| saw | the gold |
| corpus | `data/attacked` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-19T11:14:45+00:00 |

## Summary

| | |
|---|---|
| documents scored | 112 of 112 (100 %) |
| produced an invoice | 112 (100 %) |
| every field right | 112 (100 %) |
| field instances | 7252 (support 6615, correctly absent 637) |
| detection recall | 100 % |
| detection precision | 100 % |
| value accuracy | 100 % |
| accuracy | 100 % |

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
| `lines[].description` | 770 | 770 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].quantity` | 770 | 770 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].unit_price_net` | 770 | 770 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].discount` | 154 | 154 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
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
| `lines` | 4774 | 4774 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `rate_totals` | 406 | 406 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 455 | 455 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `advance` | 301 | 301 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `foreign_currency` | 609 | 609 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `mixed_rates` | 672 | 672 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `reverse_charge` | 238 | 238 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `multi_page` | 2912 | 2912 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `correction` | 476 | 476 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `split_payment` | 518 | 518 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `grosz_rounding` | 434 | 434 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `classic` | 1456 | 1456 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `compact` | 2541 | 2541 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `ledger` | 2618 | 2618 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

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

* **This is a run over an attacked corpus, where one placement makes a correct reading look wrong.** The suite prints a payload inside an item's own description cell, and that description is a scored field — so a reader that transcribes the cell perfectly still differs from the gold there, by definition rather than by behaviour. Any `lines[].description` counted wrong below may be that rather than a misreading, and the `attack.md` beside this file is where the two are told apart.
* This baseline saw **the gold**. A number produced by something that was handed the answer is a check on the harness, not a result about extraction.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
