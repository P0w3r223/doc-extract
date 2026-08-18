# Vendored schema provenance

## `fa3.xsd`

| | |
|---|---|
| What | KSeF **FA(3)** — the logical structure of the Polish structured invoice |
| Source | <http://crd.gov.pl/wzor/2025/06/25/13775/schemat.xsd> |
| Publisher | Ministerstwo Finansów, via the Centralne Repozytorium Wzorów Dokumentów |
| Published | 2025-06-25 |
| Retrieved | 2026-08-18 |
| Size | 183 798 bytes |
| SHA-256 | `b646b6b525f51adf1bb2545f111fc8ca6e7aa6dd2f98948f1667d3695c06d958` |
| Fixed attributes | `kodSystemowy="FA (3)"`, `wersjaSchemy="1-0E"` |

### The three files it imports

FA(3) is not self-contained. It imports the Ministry's shared type definitions, which in turn
include two more files — all three by absolute `crd.gov.pl` URL, so a validator handed only
`fa3.xsd` reaches the network to resolve `etd:TNrNIP`, `etd:TKodKraju` and every other elementary
type. All three are vendored beside it, and `tests/conftest.py` maps the URLs onto the local copies
so the suite compiles the schema with remote fetching **disabled**.

| File | Size | SHA-256 |
|---|---|---|
| `StrukturyDanych_v10-0E.xsd` | 31 547 B | `1137ce6e3c11c2b9ef3f05e4e72d6dcd6b4fa94908ea558f2ba15de0259bb2aa` |
| `ElementarneTypyDanych_v10-0E.xsd` | 12 228 B | `8a531cb181d3e298d11b28766655ae91fee2d7851440095932ffc82137ed2be1` |
| `KodyKrajow_v10-0E.xsd` | 40 729 B | `1d41a1b3184188f2d20a51d3afde26204dda182ec5dacf018204dcc9870dc644` |

All three come from
`http://crd.gov.pl/xml/schematy/dziedzinowe/mf/2022/01/05/eD/DefinicjeTypy/`, retrieved 2026-08-18.
The import closure is complete: `KodyKrajow` references nothing further.

In force since **2026-02-01**, when it replaced FA(2). The KSeF mandate applies from 2026-02-01 to
taxpayers whose 2024 sales exceeded 200 M PLN and from 2026-04-01 to everyone else; taxpayers under
10 000 PLN of monthly sales may defer *issuing* until the end of 2026 but must *receive* from
2026-02-01.

## Why it is vendored rather than fetched

`src/doc_extract/schema/vocab.py` is generated from this file, and `tests/test_vocab.py` re-derives
every closed domain from it and fails if the two disagree. A schema fetched at run time would make
the test suite depend on a government server being up and on the file never changing underneath it;
vendoring turns a republication into an explicit, reviewable commit instead of a silent shift in
what the code considers a valid VAT rate.

## What it does not do

The file contains **zero `xsd:assert` elements**. Being XSD 1.0, it constrains types, enumerations
and cardinality and nothing more — no arithmetic or cross-field relationship is validated. `P_15`
(the gross total) is a bare decimal with no stated link to the per-rate totals `P_13_*`/`P_14_*`,
and those have none to the line items. That gap is what `schema/invariants.py` exists to fill, and
the reason it is worth filling.

## Re-vendoring

```bash
ED=http://crd.gov.pl/xml/schematy/dziedzinowe/mf/2022/01/05/eD/DefinicjeTypy
curl -sSL -o schemas/fa3.xsd http://crd.gov.pl/wzor/2025/06/25/13775/schemat.xsd
curl -sSL -o schemas/StrukturyDanych_v10-0E.xsd      "$ED/StrukturyDanych_v10-0E.xsd"
curl -sSL -o schemas/ElementarneTypyDanych_v10-0E.xsd "$ED/ElementarneTypyDanych_v10-0E.xsd"
curl -sSL -o schemas/KodyKrajow_v10-0E.xsd            "$ED/KodyKrajow_v10-0E.xsd"
grep -ho 'schemaLocation="[^"]*"' schemas/*.xsd | sort -u   # check the closure is still complete
sha256sum schemas/*.xsd                       # update the tables above
python -m doc_extract.schema.generate_vocab   # regenerate vocab.py
pytest tests/test_vocab.py tests/test_generate_vocab.py tests/test_synth_xml.py
```

`vocab.py` is written by `doc_extract.schema.generate_vocab`, and
`tests/test_generate_vocab.py` fails if the committed file is not byte-for-byte what that command
produces. Running it with `--check` writes nothing and exits non-zero when the two have drifted, so
a re-vendor that forgot to regenerate cannot pass.
