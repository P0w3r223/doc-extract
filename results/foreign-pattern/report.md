# pattern — 108 documents

| | |
|---|---|
| baseline | `pattern` |
| answered by | `pattern` |
| saw | the page |
| corpus | `data/foreign` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-19T11:56:41+00:00 |

## Summary

| | |
|---|---|
| documents scored | 108 of 108 (100 %) |
| produced an invoice | 0 (0.0 %) |
| every field right | 0 (0.0 %) |
| field instances | 6674 (support 6066, correctly absent 608) |
| detection recall | 0.0 % |
| detection precision | — |
| value accuracy | — |
| accuracy | 0.0 % |

## Per field

| field | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kind` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `number` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `issue_date` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `sale_date` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `currency` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `total_gross` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `payment_account` | 89 | 0 | 0 | 89 | 0 | 0.0 % | — | — | 0.0 % |
| `seller.name` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `seller.nip` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `seller.address` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
| `buyer.name` | 108 | 0 | 0 | 108 | 0 | 0.0 % | — | — | 0.0 % |
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
| `header` | 737 | 0 | 0 | 737 | 0 | 0.0 % | — | — | 0.0 % |
| `seller` | 324 | 0 | 0 | 324 | 0 | 0.0 % | — | — | 0.0 % |
| `buyer` | 324 | 0 | 0 | 324 | 0 | 0.0 % | — | — | 0.0 % |
| `lines` | 4297 | 0 | 0 | 4297 | 0 | 0.0 % | — | — | 0.0 % |
| `rate_totals` | 384 | 0 | 0 | 384 | 0 | 0.0 % | — | — | 0.0 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 366 | 0 | 0 | 366 | 0 | 0.0 % | — | — | 0.0 % |
| `mixed_rates` | 628 | 0 | 0 | 628 | 0 | 0.0 % | — | — | 0.0 % |
| `correction` | 354 | 0 | 0 | 354 | 0 | 0.0 % | — | — | 0.0 % |
| `advance` | 274 | 0 | 0 | 274 | 0 | 0.0 % | — | — | 0.0 % |
| `reverse_charge` | 394 | 0 | 0 | 394 | 0 | 0.0 % | — | — | 0.0 % |
| `split_payment` | 468 | 0 | 0 | 468 | 0 | 0.0 % | — | — | 0.0 % |
| `foreign_currency` | 473 | 0 | 0 | 473 | 0 | 0.0 % | — | — | 0.0 % |
| `grosz_rounding` | 666 | 0 | 0 | 666 | 0 | 0.0 % | — | — | 0.0 % |
| `multi_page` | 2443 | 0 | 0 | 2443 | 0 | 0.0 % | — | — | 0.0 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `letterhead` | 1961 | 0 | 0 | 1961 | 0 | 0.0 % | — | — | 0.0 % |
| `statement` | 2068 | 0 | 0 | 2068 | 0 | 0.0 % | — | — | 0.0 % |
| `slip` | 2037 | 0 | 0 | 2037 | 0 | 0.0 % | — | — | 0.0 % |

## Failures and stop reasons

| failure class | documents |
|---|---:|
| `schema_invalid` | 108 |

| stop reason | documents |
|---|---:|
| `end_turn` | 108 |

## Cost

Over **every** attempt, including the ones that failed and were repaired.

| | |
|---|---:|
| attempts | 216 |
| of which repairs | 108 |
| input tokens | 0 |
| output tokens | 0 |
| cache write tokens | 0 |
| cache read tokens | 0 |

## Read this before the tables

* This baseline saw **the page**.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
