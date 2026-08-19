# claude — 108 documents

| | |
|---|---|
| baseline | `claude` |
| answered by | `claude-opus-5` |
| saw | the page |
| corpus | `data/synthetic` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-19T08:17:35+00:00 |

## Summary

| | |
|---|---|
| documents scored | 108 of 108 (100 %) |
| produced an invoice | 108 (100 %) |
| every field right | 108 (100 %) |
| field instances | 6674 (support 6066, correctly absent 608) |
| detection recall | 100 % |
| detection precision | 100 % |
| value accuracy | 100 % |
| accuracy | 100 % |

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
| `lines[].description` | 698 | 698 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].quantity` | 698 | 698 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].unit_price_net` | 698 | 698 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].discount` | 109 | 109 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].net` | 698 | 698 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].vat` | 698 | 698 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].vat_rate` | 698 | 698 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `rate_totals[].net` | 192 | 192 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `rate_totals[].vat` | 192 | 192 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per group

| group | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `header` | 737 | 737 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller` | 324 | 324 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer` | 324 | 324 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines` | 4297 | 4297 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `rate_totals` | 384 | 384 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 366 | 366 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `mixed_rates` | 628 | 628 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `correction` | 354 | 354 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `advance` | 274 | 274 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `reverse_charge` | 394 | 394 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `split_payment` | 468 | 468 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `foreign_currency` | 473 | 473 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `grosz_rounding` | 666 | 666 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `multi_page` | 2443 | 2443 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `classic` | 1961 | 1961 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `ledger` | 2068 | 2068 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `compact` | 2037 | 2037 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |

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
| input tokens | 98896 |
| output tokens | 100851 |
| cache write tokens | 0 |
| cache read tokens | 368172 |

## Read this before the tables

* This baseline saw **the page**.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
