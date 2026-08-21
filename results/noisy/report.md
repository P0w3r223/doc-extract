# noisy — 108 documents

| | |
|---|---|
| baseline | `noisy` |
| answered by | `noisy` |
| saw | the gold |
| corpus | `data/synthetic` |
| corpus seed | 20260818 |
| corpus built with | doc-extract 0.1.0, reportlab 5.0.0 |
| budgets | extract 16000, repair 8192, at most 1 repair(s) |
| started | 2026-08-20T09:21:35+00:00 |
| rate | 0.1 |

## Summary

| | |
|---|---|
| documents scored | 108 of 108 (100 %) |
| produced an invoice | 108 (100 %) |
| every field right | 36 (33.3 %) |
| field instances | 6674 (support 6066, correctly absent 608) |
| detection recall | 99.3 % |
| detection precision | 100 % |
| value accuracy | 98.3 % |
| accuracy | 97.5 % |

## Per field

| field | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `kind` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `number` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `issue_date` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `sale_date` | 108 | 97 | 11 | 0 | 0 | 100 % | 100 % | 89.8 % | 89.8 % |
| `currency` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `total_gross` | 108 | 99 | 9 | 0 | 0 | 100 % | 100 % | 91.7 % | 91.7 % |
| `payment_account` | 89 | 76 | 13 | 0 | 0 | 100 % | 100 % | 85.4 % | 85.4 % |
| `seller.name` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `seller.nip` | 108 | 94 | 14 | 0 | 0 | 100 % | 100 % | 87.0 % | 87.0 % |
| `seller.address` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.name` | 108 | 97 | 11 | 0 | 0 | 100 % | 100 % | 89.8 % | 89.8 % |
| `buyer.nip` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `buyer.address` | 108 | 108 | 0 | 0 | 0 | 100 % | 100 % | 100 % | 100 % |
| `lines[].description` | 698 | 691 | 0 | 7 | 0 | 99.0 % | 100 % | 100 % | 99.0 % |
| `lines[].quantity` | 698 | 691 | 0 | 7 | 0 | 99.0 % | 100 % | 100 % | 99.0 % |
| `lines[].unit_price_net` | 698 | 691 | 0 | 7 | 0 | 99.0 % | 100 % | 100 % | 99.0 % |
| `lines[].discount` | 109 | 107 | 0 | 2 | 0 | 98.2 % | 100 % | 100 % | 98.2 % |
| `lines[].net` | 698 | 675 | 16 | 7 | 0 | 99.0 % | 100 % | 97.7 % | 96.7 % |
| `lines[].vat` | 698 | 691 | 0 | 7 | 0 | 99.0 % | 100 % | 100 % | 99.0 % |
| `lines[].vat_rate` | 698 | 691 | 0 | 7 | 0 | 99.0 % | 100 % | 100 % | 99.0 % |
| `rate_totals[].net` | 192 | 184 | 8 | 0 | 0 | 100 % | 100 % | 95.8 % | 95.8 % |
| `rate_totals[].vat` | 192 | 169 | 23 | 0 | 0 | 100 % | 100 % | 88.0 % | 88.0 % |

## Per group

| group | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `header` | 737 | 704 | 33 | 0 | 0 | 100 % | 100 % | 95.5 % | 95.5 % |
| `seller` | 324 | 310 | 14 | 0 | 0 | 100 % | 100 % | 95.7 % | 95.7 % |
| `buyer` | 324 | 313 | 11 | 0 | 0 | 100 % | 100 % | 96.6 % | 96.6 % |
| `lines` | 4297 | 4237 | 16 | 44 | 0 | 99.0 % | 100 % | 99.6 % | 98.6 % |
| `rate_totals` | 384 | 353 | 31 | 0 | 0 | 100 % | 100 % | 91.9 % | 91.9 % |

## Per tier

| tier | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `clean` | 366 | 340 | 13 | 13 | 0 | 96.4 % | 100 % | 96.3 % | 92.9 % |
| `mixed_rates` | 628 | 613 | 15 | 0 | 0 | 100 % | 100 % | 97.6 % | 97.6 % |
| `correction` | 354 | 346 | 8 | 0 | 0 | 100 % | 100 % | 97.7 % | 97.7 % |
| `advance` | 274 | 262 | 12 | 0 | 0 | 100 % | 100 % | 95.6 % | 95.6 % |
| `reverse_charge` | 394 | 380 | 7 | 7 | 0 | 98.2 % | 100 % | 98.2 % | 96.4 % |
| `split_payment` | 468 | 444 | 12 | 12 | 0 | 97.4 % | 100 % | 97.4 % | 94.9 % |
| `foreign_currency` | 473 | 456 | 17 | 0 | 0 | 100 % | 100 % | 96.4 % | 96.4 % |
| `grosz_rounding` | 666 | 654 | 12 | 0 | 0 | 100 % | 100 % | 98.2 % | 98.2 % |
| `multi_page` | 2443 | 2422 | 9 | 12 | 0 | 99.5 % | 100 % | 99.6 % | 99.1 % |

## Per template

| template | support | correct | wrong | missed | spurious | recall | precision | value acc. | accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `classic` | 1961 | 1900 | 37 | 24 | 0 | 98.8 % | 100 % | 98.1 % | 96.9 % |
| `ledger` | 2068 | 2034 | 28 | 6 | 0 | 99.7 % | 100 % | 98.6 % | 98.4 % |
| `compact` | 2037 | 1983 | 40 | 14 | 0 | 99.3 % | 100 % | 98.0 % | 97.3 % |

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

72 of 108 documents carry at least one known error.

| kind | documents |
|---|---:|
| `total_transposed` | 9 |
| `vat_cent` | 15 |
| `rate_swapped` | 8 |
| `line_dropped` | 7 |
| `line_transposed` | 16 |
| `nip_digit` | 14 |
| `account_digit` | 13 |
| `year_misread` | 4 |
| `date_shifted` | 7 |
| `name_truncated` | 11 |

## Read this before the tables

* This baseline saw **the gold**. A number produced by something that was handed the answer is a check on the harness, not a result about extraction.
* Detection and value accuracy are separate columns on purpose. A field that is half missed and a field that is half misread both read as 50 % accuracy and need different work.
