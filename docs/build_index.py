"""Build `docs/index.html` from the repository, so every figure on the page is derived, not typed.

    python docs/build_index.py

The page states counts — assertions in the schema, rules in the detector, rows in the corpus — and
a portfolio page whose numbers were transcribed by hand is exactly the artifact this project argues
against. Everything here is read from the vendored XSD, from `schema/invariants.py`, and from the
corpus generator at its shipping defaults.
"""

from __future__ import annotations

import collections
import html
import pathlib
import re
import subprocess

from doc_extract.eval import fields
from doc_extract.eval import predictions as prediction_file
from doc_extract.eval.aggregate import Scored, summarise
from doc_extract.eval.baselines import BASELINES, BY_NAME
from doc_extract.eval.scorer import judge
from doc_extract.extract.result import FailureClass
from doc_extract.schema import vocab
from doc_extract.schema.generate_vocab import XSD_PATH
from doc_extract.synth import render
from doc_extract.synth.corpus import DEFAULT_PER_TIER, DEFAULT_SEED, documents
from doc_extract.synth.tiers import TIERS

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "index.html"
URL = "https://p0w3r223.github.io/doc-extract/"
REPO = "https://github.com/P0w3r223/doc-extract"

BAR_X, BAR_W, ROW_H = 150.0, 500.0, 26.0


def schema_facts() -> dict[str, int]:
    """What the Ministry's schema does and does not constrain."""
    text = XSD_PATH.read_text(encoding="utf-8")
    return {
        "bytes": len(text.encode("utf-8")),
        "assertions": len(re.findall(r"<xs[d]?:assert", text)),
        "simple_types": len(re.findall(r"<xs[d]?:simpleType", text)),
        "enumerations": len(re.findall(r"<xs[d]?:enumeration", text)),
    }


def rules() -> list[tuple[str, str]]:
    """Every `(rule id, severity)` the detector can report, read off the module itself."""
    source = (ROOT / "src" / "doc_extract" / "schema" / "invariants.py").read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for rule, severity in re.findall(
        r'rule=f?"([^"]+)",\s*severity=Severity\.(HARD|HEURISTIC)', source
    ):
        for expanded in ([rule] if "{" not in rule else
                         [rule.replace("{attr}", attr) for attr in ("net", "vat")]):
            found[expanded] = severity
    return sorted(found.items())


def bars(rows: list[tuple[str, float, str]], *, label_width: float = 142.0) -> str:
    """A horizontal bar chart: `(label, value, printed value)`, widest bar full width."""
    top = max((value for _, value, _ in rows), default=1) or 1
    height = int(len(rows) * ROW_H + 8)
    out = [
        f'<svg class="chart" viewBox="0 0 720 {height}" width="720" height="{height}" role="img" '
        f'xmlns="http://www.w3.org/2000/svg">'
    ]
    for index, (label, value, printed) in enumerate(rows):
        y = index * ROW_H + 15
        width = max(2.0, BAR_W * value / top)
        out.append(
            f'<text class="bar-label" x="{label_width}" y="{y + 10}" text-anchor="end">'
            f"{html.escape(label)}</text>"
            f'<rect class="bar" x="{BAR_X}" y="{y}" width="{width:.1f}" height="17" rx="2"></rect>'
            f'<text class="bar-value" x="{BAR_X + width + 6:.1f}" y="{y + 10}">'
            f"{html.escape(printed)}</text>"
        )
    return "".join(out) + "</svg>"


def ranges(rows: list[tuple[str, int, int, str]]) -> str:
    """A min-max range per label — for row counts, where the spread is the point."""
    top = max(high for _, _, high, _ in rows) or 1
    height = int(len(rows) * 32 + 40)
    out = [
        f'<svg class="chart" viewBox="0 0 720 {height}" width="720" height="{height}" role="img" '
        f'xmlns="http://www.w3.org/2000/svg">'
    ]
    for index, (label, low, high, printed) in enumerate(rows):
        y = index * 32 + 24
        x1 = BAR_X + BAR_W * low / top
        x2 = BAR_X + BAR_W * high / top
        out.append(
            f'<text class="bar-label" x="142" y="{y + 4}" text-anchor="end">'
            f"{html.escape(label)}</text>"
            f'<line class="range" x1="{x1:.1f}" x2="{max(x2, x1 + 2):.1f}" y1="{y}" y2="{y}"></line>'
            f'<circle class="range-dot" cx="{x1:.1f}" cy="{y}" r="4"></circle>'
            f'<circle class="range-dot high" cx="{max(x2, x1 + 2):.1f}" cy="{y}" r="4"></circle>'
            f'<text class="bar-value" x="{max(x2, x1 + 2) + 10:.1f}" y="{y + 4}">'
            f"{html.escape(printed)}</text>"
        )
    out.append(f'<text class="axis" x="{BAR_X}" y="{height - 8}">0</text>')
    out.append(f'<text class="axis" x="650" y="{height - 8}" text-anchor="end">{top} rows</text>')
    return "".join(out) + "</svg>"


def printed_amounts(corpus: list) -> tuple[int, int]:
    """How many of the corpus's amounts are printed with a thousands space, and how many there are.

    The figure the source layer's whole argument rests on. `render._amount` is used rather than a
    copy of the formatting rule, because a page that claimed a number about how amounts are printed
    and then printed them differently would be the failure this whole file exists to prevent.
    """
    values = [
        value
        for document in corpus
        for value in (
            [document.invoice.total_gross]
            + [total.net for total in document.invoice.rate_totals]
            + [total.vat for total in document.invoice.rate_totals]
            + [line.net for line in document.invoice.lines]
            + [line.vat for line in document.invoice.lines]
        )
    ]
    spaced = sum(1 for value in values if " " in render._amount(value))
    return spaced, len(values)


def baselines(corpus: list) -> list[dict[str, object]]:
    """Every committed run, re-scored here from its prediction file against the corpus's gold.

    Not read off a report and not typed in: the page recomputes the numbers from
    `results/<run>/predictions.jsonl`, which is the same claim the prediction files exist to support
    — that a figure can be checked without re-running a model. It also means a page built after a
    change to the scorer shows the new numbers, and a stale committed report would be visible as a
    disagreement rather than quietly reprinted.

    Gold comes from the generator in memory, so building the page needs no corpus on disk. A run made
    on a different seed is refused rather than mixed in: it would be a table whose rows describe
    different documents.
    """
    gold = {document.doc_id: document.invoice for document in corpus}
    tiers = {document.doc_id: document.tier for document in corpus}
    templates = {document.doc_id: document.template for document in corpus}

    results = ROOT / "results"
    if not results.is_dir():  # pragma: no cover — a checkout with no committed runs
        return []

    rows: list[dict[str, object]] = []
    for directory in sorted(results.iterdir()):
        predictions_path = directory / prediction_file.PREDICTIONS_NAME
        if not predictions_path.exists():
            continue
        meta = prediction_file.read_meta(directory / prediction_file.RUN_NAME)
        seed = meta.corpus.get("corpus_seed")
        if seed != DEFAULT_SEED:
            raise SystemExit(
                f"{directory.name} was scored on corpus seed {seed}, and this page is built on "
                f"{DEFAULT_SEED}; rebuild the run or leave it out of `results/`"
            )
        records = prediction_file.read(predictions_path)
        report = summarise(
            [
                Scored(
                    prediction=record,
                    score=judge(
                        gold[record.doc_id],
                        record.parse(),
                        doc_id=record.doc_id,
                        tier=tiers[record.doc_id],
                        template=templates[record.doc_id],
                        failure=FailureClass(record.failure),
                    ),
                )
                for record in records
            ],
            run=meta,
            expected=list(gold),
        )
        rows.append({
            #: A baseline is named by what it is; a real model is named by *which* model, because
            #: that is the only thing that varies between two remote runs. `claude` appearing twice
            #: would be a table whose rows a reader cannot tell apart — and comparing two models on
            #: one corpus is exactly what those rows are for.
            "name": meta.model if _is_remote(meta.baseline) else meta.baseline,
            "baseline": meta.baseline,
            "directory": directory.name,
            "sees": str(meta.options.get("sees", "unstated")),
            "extracted": report.extracted,
            "documents": report.documents,
            "exact": report.exact,
            "accuracy": report.overall.accuracy,
            "recall": report.overall.detection_recall,
            "value": report.overall.value_accuracy,
            "support": report.overall.support,
        })
    #: Declared order (B0, B1, B2, B3, then the real models), not the directory listing's. The
    #: baselines only mean anything read against each other, and `oracle` is the row the others are
    #: read against — alphabetical would open the table on `constant`. Two runs of the same baseline
    #: — two models through the identical pipeline — fall back to their directory name, so the row
    #: order is a property of the repository rather than of the filesystem's iteration order.
    order = [baseline.name for baseline in BASELINES]
    return sorted(
        rows,
        key=lambda row: (
            order.index(row["baseline"]) if row["baseline"] in order else len(order),
            row["directory"],
        ),
    )


def _is_remote(baseline: str) -> bool:
    """Whether a run called a model over the network, per the baseline registry."""
    entry = BY_NAME.get(baseline)
    return entry is not None and entry.remote


def percent(value: float | None) -> str:
    """A rate, or an em dash. Never `0 %` for an absent denominator — see `eval/aggregate.py`."""
    return "&mdash;" if value is None else f"{value * 100:.1f}&nbsp;%"


def baseline_table(rows: list[dict[str, object]]) -> str:
    if not rows:  # pragma: no cover — only when `results/` is empty
        return "<p class=\"note\">No committed runs in <code>results/</code>.</p>"
    head = (
        "<table><thead><tr><th>baseline</th><th>saw</th><th class=\"num\">invoice</th>"
        "<th class=\"num\">exact</th><th class=\"num\">recall</th><th class=\"num\">value</th>"
        "<th class=\"num\">accuracy</th></tr></thead><tbody>"
    )
    body = "".join(
        f'<tr><th><code>{html.escape(str(row["name"]))}</code></th>'
        f'<td>{html.escape(str(row["sees"]))}</td>'
        f'<td class="num">{row["extracted"]} / {row["documents"]}</td>'
        f'<td class="num">{row["exact"]}</td>'
        f'<td class="num">{percent(row["recall"])}</td>'  # type: ignore[arg-type]
        f'<td class="num">{percent(row["value"])}</td>'   # type: ignore[arg-type]
        f'<td class="num">{percent(row["accuracy"])}</td></tr>'  # type: ignore[arg-type]
        for row in rows
    )
    return head + body + "</tbody></table>"


def head_commit() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):  # pragma: no cover
        return "unknown"


def build() -> str:
    facts = schema_facts()
    every_rule = rules()
    hard = [r for r, s in every_rule if s == "HARD"]
    heuristic = [r for r, s in every_rule if s == "HEURISTIC"]
    family = collections.Counter(rule.split(".")[0] for rule, _ in every_rule)

    corpus = list(documents())
    rows_per_doc = [len(doc.invoice.lines) for doc in corpus]
    per_tier: dict[str, list[int]] = collections.defaultdict(list)
    for doc in corpus:
        per_tier[doc.tier].append(len(doc.invoice.lines))
    rate_counts = collections.Counter(
        line.vat_rate for doc in corpus for line in doc.invoice.lines
    )
    discounted = sum(
        1 for doc in corpus for line in doc.invoice.lines if line.discount is not None
    )
    templates = collections.Counter(doc.template for doc in corpus)
    kinds = collections.Counter(doc.invoice.kind for doc in corpus)
    spaced, amounts = printed_amounts(corpus)

    tier_rows = [
        (tier.name, min(per_tier[tier.name]), max(per_tier[tier.name]),
         f"{min(per_tier[tier.name])}–{max(per_tier[tier.name])}")
        for tier in TIERS
    ]
    rate_rows = [
        (code, count, f"{count} ({count / len(rows_per_doc) and count * 100 / sum(rate_counts.values()):.0f}%)")
        for code, count in rate_counts.most_common()
    ]
    family_rows = [
        (name, count, str(count))
        for name, count in sorted(family.items(), key=lambda item: -item[1])
    ]
    runs = baselines(corpus)
    scored_fields = len(fields.FIELDS)

    return TEMPLATE.format(
        url=URL,
        repo=REPO,
        commit=head_commit(),
        xsd_bytes=f"{facts['bytes']:,}".replace(",", " "),
        assertions=facts["assertions"],
        simple_types=facts["simple_types"],
        enumerations=facts["enumerations"],
        rule_count=len(every_rule),
        hard_count=len(hard),
        heuristic_count=len(heuristic),
        documents=len(corpus),
        rows=sum(rows_per_doc),
        discounted=discounted,
        discounted_pct=f"{discounted * 100 / sum(rows_per_doc):.1f}",
        spaced_amounts=spaced,
        amounts=amounts,
        spaced_pct=f"{spaced * 100 / amounts:.0f}",
        tiers=len(TIERS),
        per_tier=DEFAULT_PER_TIER,
        templates=" · ".join(f"{name} {count}" for name, count in sorted(templates.items())),
        kinds=" · ".join(f"{name} {count}" for name, count in kinds.most_common()),
        rate_codes=len(vocab.VAT_RATE_CODES),
        currencies=len(vocab.CURRENCIES),
        invoice_kinds=len(vocab.INVOICE_KINDS),
        tier_chart=ranges(tier_rows),
        rate_chart=bars(rate_rows),
        family_chart=bars(family_rows),
        hard_list=", ".join(f"<code>{html.escape(r)}</code>" for r in hard),
        heuristic_list=", ".join(f"<code>{html.escape(r)}</code>" for r in heuristic),
        baseline_table=baseline_table(runs),
        baseline_count=len(runs),
        scored_fields=scored_fields,
        field_instances=runs[0]["support"] if runs else 0,
    )


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Poland's national e-invoice schema checks nothing an accountant would &mdash; doc-extract</title>
<meta name="description" content="FA(3) is {xsd_bytes} bytes of XSD with {enumerations} enumerations and {assertions} assertions. Net plus VAT equals gross is not in it. This project turns that arithmetic into a label-free error detector.">
<meta property="og:type" content="website">
<meta property="og:title" content="Poland's national e-invoice schema checks nothing an accountant would">
<meta property="og:description" content="{enumerations} enumerations, {assertions} assertions. The consistency rules every invoice obviously satisfies are unenforced by the standard — which is what makes checking them worth doing.">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 16 16%22><text y=%2213%22 font-size=%2213%22>&#129534;</text></svg>">
<style>
/* Both colour schemes are first-class: the palette is a set of variables, and dark mode swaps the
   variables rather than restating the design. Charts inherit them, which is why they are SVG. */
:root {{
  color-scheme: light dark;
  --bg: #ffffff;
  --surface: #f6f8fa;
  --border: #e3e7ee;
  --text: #1c2430;
  --muted: #5b6472;
  --accent: #2563eb;
  --accent-soft: #93c5fd;
  --positive: #059669;
  --warn: #b45309;
  --radius: 10px;
}}

@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #0f1319;
    --surface: #161c25;
    --border: #263041;
    --text: #e6eaf2;
    --muted: #98a3b6;
    --accent: #6ea8fe;
    --accent-soft: #2c4a7c;
    --positive: #34d399;
    --warn: #fbbf24;
  }}
}}

* {{ box-sizing: border-box; }}

body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue",
    Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  max-width: 62rem;
  margin: 0 auto;
  padding: 2.5rem 1.25rem 4rem;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}}

a {{ color: var(--accent); }}
a:focus-visible, summary:focus-visible {{
  outline: 2px solid var(--accent);
  outline-offset: 3px;
  border-radius: 3px;
}}

.eyebrow {{
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--muted);
  margin: 0 0 0.5rem;
}}

h1 {{
  font-size: clamp(1.75rem, 1.2rem + 2.2vw, 2.75rem);
  line-height: 1.15;
  letter-spacing: -0.02em;
  margin: 0 0 0.75rem;
}}

h2 {{
  font-size: 1.3rem;
  letter-spacing: -0.01em;
  margin: 2.75rem 0 0.35rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border);
}}

h2:first-of-type {{ border-top: none; padding-top: 0; }}
h3 {{ font-size: 1rem; margin: 1.5rem 0 0.25rem; }}
p {{ margin: 0.5rem 0; }}
.lead {{ font-size: 1.1rem; color: var(--muted); max-width: 46rem; }}
.note {{ color: var(--muted); font-size: 0.9rem; }}
.hint {{ display: block; color: var(--muted); font-size: 0.85rem; font-weight: 400; }}

.kpis {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: 0.75rem;
  margin: 1.75rem 0;
  padding: 0;
  list-style: none;
}}

.kpi {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.9rem 1rem;
}}

.kpi-value {{ font-size: 1.6rem; font-weight: 700; letter-spacing: -0.02em; }}
.kpi-label {{ font-size: 0.85rem; font-weight: 600; }}
.kpi-note {{ font-size: 0.78rem; color: var(--muted); line-height: 1.35; }}

.card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.2rem;
  margin: 1.25rem 0;
}}

.card.caution {{ border-left: 3px solid var(--warn); }}

figure {{ margin: 1rem 0 0; }}
figcaption {{ color: var(--muted); font-size: 0.85rem; margin-top: 0.35rem; }}

.chart-wrap {{ overflow-x: auto; }}
.chart {{ max-width: 100%; height: auto; display: block; }}
.chart text {{ font-size: 11px; fill: var(--text); }}
.chart .bar-label {{ fill: var(--text); }}
.chart .bar-value, .chart .axis {{ fill: var(--muted); font-size: 10.5px; }}
.chart .bar {{ fill: var(--accent); }}
.chart .range {{ stroke: var(--accent); stroke-width: 6; stroke-linecap: round; }}
.chart .range-dot {{ fill: var(--accent); }}
.chart .range-dot.high {{ fill: var(--accent); opacity: 0.55; }}

table {{ border-collapse: collapse; width: 100%; font-size: 0.92rem; }}
th, td {{ text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid var(--border); }}
th {{ font-weight: 600; color: var(--muted); font-size: 0.82rem; }}
td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}

details {{ margin: 0.75rem 0; }}
summary {{ cursor: pointer; font-size: 0.9rem; color: var(--accent); }}
pre {{
  overflow-x: auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.85rem 1rem;
  font-size: 0.8rem;
  line-height: 1.5;
}}
code {{ font-size: 0.9em; }}

footer {{
  margin-top: 3rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.85rem;
}}

@media print {{
  body {{ max-width: none; }}
  details {{ display: none; }}
}}
</style>
</head>
<body>
<header>
  <p class="eyebrow">P5 &middot; KSeF FA(3) &middot; milestones 1&ndash;4 of 7</p>
  <h1>Poland's national e-invoice schema checks nothing an accountant would</h1>
  <p class="lead">FA(3) &mdash; mandatory since 2026 &mdash; is {xsd_bytes} bytes of XSD carrying
  {enumerations} enumerations and <strong>{assertions} assertions</strong>. It knows what shape an
  invoice is. It does not know that net plus VAT equals gross. This project treats that unenforced
  arithmetic as a <strong>label-free error detector</strong>: a signal available on every document,
  including the ones nobody annotated.</p>
</header>

<ul class="kpis">
  <li class="kpi">
    <div class="kpi-value">{assertions}</div>
    <div class="kpi-label">Assertions in the standard</div>
    <div class="kpi-note">in {xsd_bytes} bytes; XSD 1.0 has no way to express one</div>
  </li>
  <li class="kpi">
    <div class="kpi-value">{rule_count}</div>
    <div class="kpi-label">Consistency rules added</div>
    <div class="kpi-note">{hard_count} arithmetic identities, {heuristic_count} heuristics, counted apart</div>
  </li>
  <li class="kpi">
    <div class="kpi-value">{documents}</div>
    <div class="kpi-label">Documents generated</div>
    <div class="kpi-note">{rows} rows, gold with no annotation step</div>
  </li>
  <li class="kpi">
    <div class="kpi-value">5 / 7</div>
    <div class="kpi-label">Milestones built</div>
    <div class="kpi-note">the gate is measured; injection and the real set are not</div>
  </li>
</ul>

<div class="card caution">
  <strong>This is a project in progress, and the page says so on purpose.</strong> What exists is
  the domain layer, the corpus generator, the extraction pipeline, the scorer and the first half of
  the detector study, grounding and the routing gate. Everything but one command runs offline with
  no network and no API key; that command has been run, and <strong><code>claude-opus-5</code>
  reads all 108 documents perfectly</strong>.
  <br><br>
  That is a result about the corpus as much as about the model. The nine tiers vary what an invoice
  <em>means</em> &mdash; grosz rounding, corrections, reverse charge, multiple pages &mdash; not how
  hard the page is to <em>read</em>. With no errors left to find, the detector has nothing to detect
  on that run, so the headline question is answered on a second arm: the same corpus and the same
  pipeline, with a weaker model. Grounding, routing and the coverage&ndash;accuracy curve are the
  rest of milestone 5; the injection suite is milestone 6 and is <em>not built</em>.
</div>

<h2>Does &ldquo;the arithmetic holds&rdquo; predict &ldquo;the fields are right&rdquo;?</h2>
<p>The project's headline question, asked of <code>claude-haiku-4-5</code>, which gets 42 of 107
documents wrong and so supplies a real, unlabelled model-error population. The invariants are run on
the <strong>prediction</strong>, never on the gold &mdash; the signal has to be available at
inference time on a document nobody annotated.</p>
<table>
  <thead><tr><th></th><th class="num">flagged</th><th class="num">silent</th></tr></thead>
  <tbody>
    <tr><th>fields wrong</th><td class="num">32</td><td class="num">10</td></tr>
    <tr><th>fields right</th><td class="num">0</td><td class="num">65</td></tr>
  </tbody>
</table>
<p><strong>Precision 100.0&nbsp;%, recall 76.2&nbsp;%, zero false positives</strong>, and all 32
catches point at a field that is genuinely wrong.</p>
<p class="note">The recall is not a property of the detector. It is the fraction of that model's
mistakes that happened to land on numeric fields. The 25 catches on <code>payment_account</code> are
the IBAN mod-97 check digit; 9 more are row arithmetic catching a misread discount. Every one of the
ten misses is a <strong>name or a description</strong> &mdash; a field with no redundancy behind it
for arithmetic to check &mdash; and eight of those sit in the multi-page tier, where a description
wraps across a page break. Not one arithmetic error escaped.</p>
<p>That is the case for the grounding layer, arrived at by measurement rather than assumed: it
covers exactly the fields the arithmetic cannot see, because a description the model invented is a
value that resolves to no span on the page.</p>
<p class="note">Two cautions the study prints beside its own numbers. The <strong>heuristic rules
have never fired on any run</strong> &mdash; reported as a dash rather than pooled with the hard
rules, and either the corpus needs a tier that exercises them or they need dropping, because a
metric identical across every variant is broken rather than stable. And a <strong>confidently wrong
but internally consistent answer is invisible</strong>: the constant baseline sits at prevalence
100&nbsp;% with recall 0&nbsp;%.</p>

<h2>The gap this fills</h2>
<p>The schema published by the Ministry of Finance is XSD 1.0. That version has no
<code>assert</code> element at all, so a conforming validator checks types, enumerations and
cardinality &mdash; and stops. <code>P_15</code>, the gross total, is a bare decimal with no stated
relationship to the per-rate totals, and those have none to the line items.</p>

<table>
  <tbody>
    <tr><th>Bytes of vendored schema</th><td class="num">{xsd_bytes}</td></tr>
    <tr><th>Simple types defined</th><td class="num">{simple_types}</td></tr>
    <tr><th>Enumerated values <span class="hint">closed domains: rates, currencies, invoice kinds</span></th><td class="num">{enumerations}</td></tr>
    <tr><th><code>xsd:assert</code> elements <span class="hint">every cross-field rule an invoice satisfies is unenforced</span></th><td class="num">{assertions}</td></tr>
  </tbody>
</table>
<p class="note">Checking those rules is therefore real work rather than a re-run of validation that
already exists. The schema is vendored in the repository with its SHA-256, and a test enforces the
digest &mdash; so this claim is checkable rather than asserted.</p>

<h2>What is checked instead</h2>
<p>{rule_count} rules, reported as <em>data</em> rather than raised as errors. A model that refused
to construct a broken invoice could not be routed, measured or explained &mdash; and inspecting
broken invoices is the entire project.</p>
<figure>
  <div class="chart-wrap">{family_chart}</div>
  <figcaption>Rules by family. Each carries a stable id, so per-rule precision and recall can be
  tracked instead of collapsing into one &ldquo;invalid&rdquo; flag.</figcaption>
</figure>
<p><strong>Severity is part of the design, not decoration.</strong> A hard rule is an arithmetic
identity: a violation means something is genuinely wrong. A heuristic usually holds but has lawful
exceptions &mdash; a <em>faktura uproszczona</em> really may carry a total and nothing else. Mixing
the two would blunt the detector, because a heuristic's false positives would be indistinguishable
from a real arithmetic miss.</p>
<details>
  <summary>All {rule_count} rule ids</summary>
  <p class="note"><strong>Hard ({hard_count}):</strong> {hard_list}</p>
  <p class="note"><strong>Heuristic ({heuristic_count}):</strong> {heuristic_list}</p>
</details>

<h2>The corpus</h2>
<p>Ground truth and the rendered page come from <strong>one artifact</strong>: the generator writes
a document that validates against the vendored XSD, and the same file read back through the
extraction schema <em>is</em> the gold. There is no annotation step, so there is no annotation noise
to confuse with model error &mdash; which is what makes the detector study interpretable at all.</p>
<figure>
  <div class="chart-wrap">{tier_chart}</div>
  <figcaption>Rows per document, by difficulty tier ({per_tier} documents each). Difficulty is a
  controlled variable rather than an unlabelled mixture, so accuracy can be plotted against it.</figcaption>
</figure>
<figure>
  <div class="chart-wrap">{rate_chart}</div>
  <figcaption>VAT rate codes drawn across {rows} rows. <code>oo</code> is reverse charge,
  <code>zw</code> exempt, <code>0 WDT</code> an intra-EU supply &mdash; three ways of levying no tax
  that mean different things in law.</figcaption>
</figure>

<table>
  <tbody>
    <tr><th>Documents</th><td class="num">{documents}</td></tr>
    <tr><th>Tiers &times; documents each</th><td class="num">{tiers} &times; {per_tier}</td></tr>
    <tr><th>Layouts <span class="hint">every tier appears in each, so a per-tier result is never a per-template one in disguise</span></th><td class="num">{templates}</td></tr>
    <tr><th>Invoice kinds drawn</th><td class="num">{kinds}</td></tr>
    <tr><th>Rows carrying a discount <span class="hint">folded into the net, so a page omitting it contradicts its own arithmetic</span></th><td class="num">{discounted} ({discounted_pct}%)</td></tr>
    <tr><th>Gold documents breaking any rule <span class="hint">asserted on the seeds the corpus actually ships</span></th><td class="num">0</td></tr>
  </tbody>
</table>

<h2>What the corpus deliberately does not do</h2>
<p>It is <strong>not sanitised to be easy to parse</strong>. A quantity of 3 printed beside a price
of 466,62 reads as <code>3&nbsp;466,62</code> in a flat text dump, because a space is also Poland's
thousands separator. That ambiguity is in real invoices and it stays in this one; the source layer
resolves it from word geometry rather than by having the generator avoid it.</p>
<p>It is not a rare case: <strong>{spaced_amounts} of the {amounts} amounts</strong> the corpus
prints ({spaced_pct}%) carry that thousands space. The source layer reads each of them back as one
field, and reads a quantity printed beside a price as two &mdash; from the boxes the words occupy,
not from the string. The separation is not a tuned threshold either: a space is 0.32&nbsp;em wide,
while every column gap in the corpus is at least 12&nbsp;pt, because each cell is asserted to fit
its column with reportlab's padding still to spare.</p>
<p>What it does <em>not</em> have is real-world visual chaos &mdash; skew, stamps, poor scans,
layouts no template anticipated. Milestone 7's real held-out set exists to measure how much that
costs, and the gap will be reported whichever way it comes out.</p>

<h2>What the baselines say, and what the model says</h2>
<p>{baseline_count} committed runs over the same {documents} documents, scoring
{scored_fields} fields per invoice and {field_instances} gold field instances in total. Every row
answers in the same wire format and goes through the same prompt, parse, validation and repair
loop, so a column is comparable down the table. The numbers are recomputed for this page from each
run's committed <code>predictions.jsonl</code> &mdash; not copied from a report.</p>
{baseline_table}
<p class="note"><strong>recall</strong> is how many of the values on the page the prediction offered
a value for; <strong>value</strong> is how many of those it read correctly; <strong>accuracy</strong>
is the two together. They are separate columns because a field that is half missed and a field that
is half misread read the same in one number and need different work. A dash means there was no
denominator &mdash; never a zero, which would read as a measurement nobody made.</p>
<p><code>oracle</code> is handed the gold, so its 100&nbsp;% is a check on the harness rather than a
result: if a perfect reading scored anything less, every other number here would be wrong.
<code>constant</code> answers the same lawful invoice for every document &mdash; the floor, and a
diagnostic, because the fields it still scores well on (currency, invoice kind) are fields where the
corpus's own distribution does most of the work. <code>pattern</code> is regular expressions and
column positions with no model at all, and it was deliberately allowed to match the labels this
project's own renderer prints, which the extraction prompt is forbidden to know: it is the strongest
thing that is not a language model, and therefore the bar. <code>noisy</code> is the gold with known
errors injected at a fixed rate &mdash; not a competitor but the labelled error set the detector study
needs, since a detector measured only on a model's unlabelled mistakes is measured on a sample nobody
chose.</p>
<p><code>claude-opus-5</code> is the system under test, and it ties the oracle: every field of every
document, for $3.20. Its only divergence from the gold's own serialisation is 63 trailing zeros
&mdash; it writes <code>137.30</code> where the generator stored <code>137.3</code>, which is what
the page prints and what the scorer's amount comparison was already defined to treat as the same
quantity. A corpus that the strongest non-model reader finds hard and a frontier model finds trivial
is measuring layout parsing, not reading.</p>

<h2>What is not built yet</h2>
<p>Stated plainly, because a portfolio page that reads as finished when it is not is worse than no
page at all.</p>
<table>
  <tbody>
    <tr><th>M3 &mdash; source layer, extraction, structured output with an owned schema retry</th><td class="num">built</td></tr>
    <tr><th>M4 &mdash; pure scorer, per-field metrics with support, failure taxonomy, baselines</th><td class="num">built, model run</td></tr>
    <tr><th>M5 &mdash; <strong>the detector study</strong>, grounding, routing, the coverage&ndash;accuracy curve</th><td class="num">built</td></tr>
    <tr><th>M6 &mdash; prompt-injection suite and attack success rate</th><td class="num">not built</td></tr>
    <tr><th>M7 &mdash; real held-out set and the reported synthetic&harr;real gap</th><td class="num">not built</td></tr>
  </tbody>
</table>
<p class="note">The headline question &mdash; does &ldquo;the invariants hold&rdquo; actually predict
&ldquo;the fields are correct&rdquo;? &mdash; is measurable now, and the first answer is an awkward
one: on the run that matters most there is nothing to predict, because the model made no mistakes.
The question is being answered instead against injected errors, a weaker reader, and M7's real set.
A negative result is a publishable result, and so is a corpus that turned out to be too easy.</p>

<h2>Reproduce it</h2>
<pre><code>git clone {repo}
cd doc-extract
python -m venv .venv &amp;&amp; .venv/Scripts/python -m pip install -e ".[dev]"
pytest                                             # the figures above are assertions
python -m doc_extract.synth --out data/synthetic   # {documents} documents, reproducible from one seed
python -m doc_extract.eval run --baseline pattern  # predict, score, write results/pattern/
python docs/build_index.py                         # rebuild this page from the repository</code></pre>
<p class="note">The corpus is not committed: it is a function of one integer, so a seed in the
manifest is a smaller and more honest artifact than several hundred PDFs in git history. The
manifest also records the reportlab version and the font digests, because every rendered byte
depends on them.</p>

<footer>
  <p><a href="{repo}">Source on GitHub</a> &middot; built from
  <code>{commit}</code> &middot; part of a
  <a href="https://github.com/P0w3r223/current_projects">portfolio index</a></p>
  <p>Vendored schema &copy; Ministerstwo Finans&oacute;w, via the Centralne Repozytorium
  Wzor&oacute;w Dokument&oacute;w. Every figure on this page is generated from the repository by
  <code>docs/build_index.py</code>.</p>
</footer>
</body>
</html>
"""


def main() -> int:
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
