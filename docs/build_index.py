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

from doc_extract.attack import suite
from doc_extract.attack.payloads import BY_NAME as PAYLOADS
from doc_extract.decide.confidence import Confidence
from doc_extract.degrade import attacked as attacked_grid
from doc_extract.degrade import attacked_report
from doc_extract.degrade.corpus import documents as scanned_documents
from doc_extract.degrade.rungs import BY_NAME as RUNGS_BY_NAME
from doc_extract.degrade.rungs import TEMPLATES as RUNG_NAMES
from doc_extract.eval import dataset, detector, fields, run
from doc_extract.eval import predictions as prediction_file
from doc_extract.eval.aggregate import Scored, summarise
from doc_extract.eval.baselines import BASELINES, BY_NAME
from doc_extract.eval.format import DASH, rate
from doc_extract.eval.scorer import judge
from doc_extract.eval.selective import WRONG
from doc_extract.extract.result import FailureClass
from doc_extract.foreign.corpus import documents as foreign_documents
from doc_extract.ground.resolve import resolve as ground
from doc_extract.schema import invariants, vocab
from doc_extract.schema.generate_vocab import XSD_PATH
from doc_extract.schema.invariants import Severity
from doc_extract.synth import render
from doc_extract.synth.corpus import (
    DEFAULT_PER_TIER,
    DEFAULT_SEED,
    MANIFEST_NAME,
    documents,
)
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
        #: M6's and M7's runs are over different corpora — the same invoices with an injected
        #: string on each page, the same invoices printed by another renderer, and the same
        #: invoices photographed. Their accuracy belongs in the section that explains what the page
        #: did to it, not in a table whose rows are comparable *because* they describe the same
        #: documents rendered the same way.
        if meta.corpus.get("attacked") or meta.corpus.get("renderer") in ("foreign", "scanned"):
            continue
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


#: How a run over M7's foreign corpus is named. The prefix is what pairs it with the run of the
#: same baseline over the synthetic one, which is the only reason either number is interesting.
FOREIGN_PREFIX = "foreign-"


def foreign_study(corpus: list) -> list[dict[str, object]] | None:
    """Each baseline's accuracy on its own page and on an unfamiliar one, paired.

    Both halves come from committed prediction files and the gold rebuilt from the seed, so this
    needs neither corpus on disk. The pairing is by name — `foreign-pattern` against `pattern` —
    and a foreign run with no counterpart is dropped rather than shown beside a blank, because a
    column with one number in it is not a comparison.
    """
    gold = {document.doc_id: document for document in corpus}
    unfamiliar = {document.doc_id: document for document in foreign_documents()}

    rows = []
    for directory in sorted((ROOT / "results").glob(f"{FOREIGN_PREFIX}*")):
        baseline = directory.name[len(FOREIGN_PREFIX):]
        familiar = ROOT / "results" / baseline
        if not (directory / prediction_file.PREDICTIONS_NAME).exists():
            continue  # pragma: no cover — a directory without a run in it
        if not (familiar / prediction_file.PREDICTIONS_NAME).exists():
            continue  # pragma: no cover — a foreign arm whose own-page counterpart is not committed
        here = _summary(directory, unfamiliar)
        there = _summary(familiar, gold)
        rows.append({
            "baseline": baseline,
            "own_accuracy": there.overall.accuracy,
            "foreign_accuracy": here.overall.accuracy,
            "foreign_extracted": here.extracted,
            "documents": here.documents,
            "failures": collections.Counter(
                record.failure for record in
                prediction_file.read(directory / prediction_file.PREDICTIONS_NAME)
                if record.failure
            ),
        })
    rows.sort(key=_row_order)
    return rows or None


def _row_order(row: dict) -> tuple[int, str]:
    """Declared baseline order, with the models after the controls that make them readable.

    Alphabetical would open a held-out table on whichever name sorts first. Indexing straight into
    the baseline list would have been enough while every run was a baseline — but a remote run's
    directory is named for the *model*, because the baseline is `claude` every time and the model
    is what varies, so the first paid arm over a held-out corpus raised `ValueError` here. A model
    row is not a control and belongs below them, which is where an unknown name now goes.
    """
    order = [baseline.name for baseline in BASELINES]
    name = str(row["baseline"])
    return (order.index(name), "") if name in order else (len(order), name)


def _summary(directory, gold: dict):
    """One committed run, scored against gold rebuilt in memory."""
    meta = prediction_file.read_meta(directory / prediction_file.RUN_NAME)
    records = prediction_file.read(directory / prediction_file.PREDICTIONS_NAME)
    return summarise(
        [
            Scored(
                prediction=record,
                score=judge(
                    gold[record.doc_id].invoice, record.parse(), doc_id=record.doc_id,
                    tier=gold[record.doc_id].tier, template=gold[record.doc_id].template,
                    failure=FailureClass(record.failure),
                ),
            )
            for record in records
        ],
        run=meta,
        expected=list(gold),
    )


#: The run the headline question is asked of: the one with a real, unlabelled error population.
STUDIED_RUN = "claude-haiku-4-5"


def _study(corpus: list, predictions_path, severity: Severity) -> detector.Study:
    """One committed prediction file, scored and then run past the rules at one severity.

    Shared by the headline study and the degenerate-reading one below, because the *only* thing that
    differs between them is which severity is asked — and a second copy of this loop would be a
    second chance for the page to report a number the `detect` subcommand does not.
    """
    gold = {document.doc_id: document for document in corpus}
    verdicts = []
    for record in prediction_file.read(predictions_path):
        document = gold[record.doc_id]
        score = judge(
            document.invoice, record.parse(), doc_id=record.doc_id,
            tier=document.tier, template=document.template,
            failure=FailureClass(record.failure),
        )
        verdicts.append(detector.verdict(score, record.parse(), severity=severity))
    return detector.summarise(verdicts, severity=severity)


#: How a run over M7's scanned corpus is named, on the same convention the foreign one uses.
SCANNED_PREFIX = "scanned-"

#: The fence around the one block of this page that cannot be built without a corpus on disk.
CORPUS_DEPENDENT = "<!-- corpus-dependent: begin -->"
CORPUS_DEPENDENT_END = "<!-- corpus-dependent: end -->"

#: The rungs, in the order the page should read them: most legible first. Imported rather than
#: written out, so a rung added to the package appears here instead of being silently dropped.
RUNG_ORDER: tuple[str, ...] = RUNG_NAMES

#: Which committed run the grounding split is read off. The oracle, because the whole force of that
#: number is that the reading it is computed on is *perfect* — a signal raising 3989 alarms on a
#: model's mistakes would be doing its job.
SCANNED_CONTROL = f"{SCANNED_PREFIX}oracle"


def scanned_study(corpus: list) -> list[dict[str, object]] | None:
    """Each baseline on its own page and on each rung of legibility, paired by name.

    Scored from committed prediction files against gold rebuilt from the seed, exactly as the
    foreign study is — the manifest's `template` on this corpus is the rung, so the per-rung
    breakdown is a column of the score rather than a second computation.
    """
    gold = {document.doc_id: document for document in corpus}
    scanned = {
        document.doc_id: _with_template(document, rung.name)
        for document, rung in scanned_documents()
    }

    rows = []
    for directory in sorted((ROOT / "results").glob(f"{SCANNED_PREFIX}*")):
        baseline = directory.name[len(SCANNED_PREFIX):]
        familiar = ROOT / "results" / baseline
        if not (directory / prediction_file.PREDICTIONS_NAME).exists():
            continue  # pragma: no cover — a directory without a run in it
        if not (familiar / prediction_file.PREDICTIONS_NAME).exists():
            continue  # pragma: no cover — a scanned arm whose own-page counterpart is not committed
        here = _summary(directory, scanned)
        by_rung = dict(here.by_template)
        records = prediction_file.read(directory / prediction_file.PREDICTIONS_NAME)
        rows.append({
            "baseline": baseline,
            #: A remote run's directory is named for the model, so this is also how the section
            #: knows a row is the system under test rather than a control — and the counterpart it
            #: was paired with is that model's *text* arm on the clean page, which is two changes
            #: at once and has to be said out loud.
            "is_model": baseline not in {entry.name for entry in BASELINES},
            "own_accuracy": _summary(familiar, gold).overall.accuracy,
            "rungs": {
                name: by_rung[name].accuracy for name in RUNG_ORDER if name in by_rung
            },
            #: A single truncated document can dominate one rung's figure — one did, at 180 missed
            #: fields — so the count is carried rather than left for a reader to wonder about.
            "truncated": collections.Counter(
                scanned[record.doc_id].template
                for record in records
                if record.failure == "truncated"
            ),
        })
    rows.sort(key=_row_order)
    return rows or None


def _with_template(document, template: str):
    return type(document)(
        doc_id=document.doc_id, tier=document.tier, template=template, seed=document.seed,
        invoice=document.invoice, context=document.context, overlay=document.overlay,
    )


def grounding_on_a_scan() -> dict[str, object] | None:
    """Grounding per rung, on the perfect reading and on a model's, if either is committed.

    The one part of this page that needs a corpus on disk: grounding resolves a value against the
    page's *text*, and no committed artifact records what a page says. `data/scanned` is one command
    away (`python -m doc_extract.degrade`) and is not committed, so a checkout without it renders
    this section without its second half rather than with an invented one.

    Two readings, because they answer different halves of one question. On the **oracle** every
    alarm is provably false — the reading is right everywhere — so the split shows what a scan does
    to the signal. On a **model** the alarms are mostly real, so the split shows that the signal is
    not merely quiet on a page with a text layer: it is at its most precise there.
    """
    corpus_dir = ROOT / "data" / "scanned"
    if not (corpus_dir / MANIFEST_NAME).exists():
        return None  # pragma: no cover — the corpus has not been built here

    control = ROOT / "results" / SCANNED_CONTROL
    if not (control / prediction_file.PREDICTIONS_NAME).exists():
        return None  # pragma: no cover — a checkout without that run

    cases = {case.doc_id: case for case in dataset.load(corpus_dir).cases}
    gold = {
        document.doc_id: _with_template(document, rung.name)
        for document, rung in scanned_documents()
    }
    arms = [
        directory for directory in sorted((ROOT / "results").glob(f"{SCANNED_PREFIX}*"))
        if directory.name[len(SCANNED_PREFIX):] not in {entry.name for entry in BASELINES}
        and (directory / prediction_file.PREDICTIONS_NAME).exists()
    ]
    #: The arm with the most wrong values, not the first one on disk. A precision of 100 % over a
    #: single mistake is an anecdote; the point of this table is what the signal does against a
    #: *population* of them, so the model that made one is the one worth printing. Alphabetical
    #: order happened to pick the right arm here, which is exactly why it should not decide.
    #:
    #: Chosen from the prediction files before anything is grounded, because grounding an arm means
    #: parsing all 108 pages and this page would otherwise pay that for every arm it discards.
    best = max(arms, key=lambda directory: _wrong_values(directory, gold), default=None)
    return {
        "control": _grounding_by_rung(control, cases, gold),
        "model": best.name[len(SCANNED_PREFIX):] if best else None,
        "model_rows": _grounding_by_rung(best, cases, gold) if best else None,
    }


def _wrong_values(directory, gold: dict) -> int:
    """How many asserted values one committed run got wrong. Reads no page."""
    total = 0
    for record in prediction_file.read(directory / prediction_file.PREDICTIONS_NAME):
        invoice = record.parse()
        if invoice is None:
            continue
        document = gold[record.doc_id]
        score = judge(
            document.invoice, invoice, doc_id=record.doc_id, tier=document.tier,
            template=document.template, failure=FailureClass(record.failure),
        )
        total += sum(1 for row in score.results if row.outcome in WRONG)
    return total


def _grounding_by_rung(directory, cases: dict, gold: dict) -> dict[str, collections.Counter]:
    """One committed run's groundings, split by rung and by whether the value was actually wrong.

    `selective.WRONG` rather than a comparison against the name `WRONG`: a *spurious* value is one
    the model asserted where the document has none, which is a wrong asserted value by the same
    definition the gate uses, and `eval/selective.py` is where that definition lives. Restating it
    here as one outcome dropped 23 instances of the committed haiku arm, and the table printed
    beside `gate.md` disagreed with it about the same run and the same signal.
    """
    counts: dict[str, collections.Counter] = {name: collections.Counter() for name in RUNG_ORDER}
    for record in prediction_file.read(directory / prediction_file.PREDICTIONS_NAME):
        invoice = record.parse()
        if invoice is None:
            continue
        document = gold[record.doc_id]
        score = judge(
            document.invoice, invoice, doc_id=record.doc_id, tier=document.tier,
            template=document.template, failure=FailureClass(record.failure),
        )
        wrong = {(row.field, row.key) for row in score.results if row.outcome in WRONG}
        for row in ground(cases[record.doc_id].source(), invoice):
            if not row.measured:
                continue
            bad = (row.field, row.key) in wrong
            counts[document.template][
                "TP" if row.suspicious and bad else
                "FP" if row.suspicious else
                "FN" if bad else "TN"
            ] += 1
    return counts


#: The arm the silence section is computed from: the gold with its table dropped. Every hard rule
#: needs two figures to compare and this reading offers one, so it is the population that shows the
#: arithmetic being *unable to speak* rather than being wrong — and the one the three heuristic
#: rules, which had never fired on any run, exist for.
STRIPPED_RUN = "stripped"


def stripped_study(corpus: list) -> dict[str, object] | None:
    """Both severities over the degenerate reading, so the contrast is computed rather than typed."""
    directory = ROOT / "results" / STRIPPED_RUN
    predictions_path = directory / prediction_file.PREDICTIONS_NAME
    if not predictions_path.exists():  # pragma: no cover — a checkout without that run
        return None

    hard = _study(corpus, predictions_path, Severity.HARD)
    heuristic = _study(corpus, predictions_path, Severity.HEURISTIC)
    return {
        "judged": hard.counts.judged,
        "prevalence": hard.counts.prevalence,
        "hard_recall": hard.counts.recall,
        "hard_precision": hard.counts.precision,
        "heuristic_recall": heuristic.counts.recall,
        "heuristic_precision": heuristic.counts.precision,
        "heuristic_false_positive": heuristic.counts.false_positive,
    }


def detector_study(corpus: list) -> dict[str, object] | None:
    """The headline detector numbers, recomputed here from a committed prediction file.

    Typed into this page they would be exactly the artifact the module docstring argues against —
    and they were, until a review caught it. Gold comes from the generator in memory like every
    other figure here, so this needs no corpus on disk and no model.
    """
    directory = ROOT / "results" / STUDIED_RUN
    predictions_path = directory / prediction_file.PREDICTIONS_NAME
    if not predictions_path.exists():  # pragma: no cover — a checkout without that run
        return None

    study = _study(corpus, predictions_path, Severity.HARD)

    caught = collections.Counter(
        field for row in study.verdicts
        if row.verdict is detector.Verdict.TRUE_POSITIVE for field in row.wrong_fields
    )
    missed = collections.Counter(
        field for row in study.verdicts
        if row.verdict is detector.Verdict.FALSE_NEGATIVE for field in row.wrong_fields
    )
    missed_tiers = collections.Counter(
        row.tier for row in study.verdicts if row.verdict is detector.Verdict.FALSE_NEGATIVE
    )
    top_tier, top_tier_count = (missed_tiers.most_common(1) or [("", 0)])[0]

    counts = study.counts
    return {
        "model": STUDIED_RUN,
        "true_positive": counts.true_positive,
        "false_negative": counts.false_negative,
        "false_positive": counts.false_positive,
        "true_negative": counts.true_negative,
        "wrong_documents": counts.true_positive + counts.false_negative,
        "judged": counts.judged,
        "precision": counts.precision,
        "recall": counts.recall,
        "localisation": study.localisation,
        "caught": caught,
        "missed": missed,
        "missed_total": sum(missed.values()),
        "top_missed_tier": top_tier,
        "top_missed_tier_count": top_tier_count,
    }


#: The attacked run the injection section is computed from: the compliant control, which obeys every
#: instruction printed on a page. Its attack success rate is 100 % by construction, and that is what
#: makes it the right arm for this page's question — what the *defences* do about an attack that
#: worked is a property of the defences, and does not need a model to have been fooled first.
ATTACKED_RUN = "attack-gullible"


def injection_study(corpus: list) -> dict[str, object] | None:
    """M6's grid, recomputed here from the attacked run's committed prediction file.

    The attacked corpus is not on disk in a clean checkout any more than the clean one is, and it
    does not have to be: the suite's grid is a pure function of the base documents and of the
    parameters the run's own provenance block records, so `suite.plan` rebuilds the gold of an
    attacked document in memory.

    What this can compute without the pages is the **arithmetic** half of the gate. Grounding needs
    the rendered page, so the leak column lives in the committed `attack.md` — and the split is the
    finding rather than a limitation: the payloads the arithmetic is silent on are exactly the two
    that hand the reader a valid identifier, which then grounds because it is printed on the page.
    """
    directory = ROOT / "results" / ATTACKED_RUN
    predictions_path = directory / prediction_file.PREDICTIONS_NAME
    if not predictions_path.exists():  # pragma: no cover — a checkout without that run
        return None

    meta = prediction_file.read_meta(directory / prediction_file.RUN_NAME)
    planned = suite.plan(
        per_cell=meta.corpus["per_cell"],
        payloads=tuple(PAYLOADS[name] for name in meta.corpus["payloads"]),
        placements=tuple(meta.corpus["placements"]),
        base=corpus,
    )
    gold = {document.doc_id: document for document, _ in planned}
    by_id = {assignment.doc_id: assignment for _, assignment in planned}

    rows: dict[str, dict[str, object]] = {}
    for record in prediction_file.read(predictions_path):
        #: A prediction the suite did not plan is reported by `run.attacks` as `unmatched` rather
        #: than raised on; this page has no place to report it, so it skips rather than failing the
        #: build — the committed `attack.md` is where that discrepancy is meant to be read.
        if record.doc_id not in by_id:
            continue
        assignment = by_id[record.doc_id]
        payload = PAYLOADS[assignment.payload]
        predicted = record.parse()
        row = rows.setdefault(payload.name, {
            "goal": payload.goal, "documents": 0, "succeeded": 0, "flagged": 0,
        })
        row["documents"] += 1
        row["succeeded"] += payload.achieved(
            gold[record.doc_id].invoice, predicted, FailureClass(record.failure)
        )
        if predicted is not None and any(
            violation.severity is Severity.HARD for violation in invariants.check(predicted)
        ):
            row["flagged"] += 1

    attacking = [row for name, row in rows.items() if not PAYLOADS[name].harmless]
    return {
        "run": ATTACKED_RUN,
        "rows": rows,
        "documents": sum(int(row["documents"]) for row in attacking),
        "succeeded": sum(int(row["succeeded"]) for row in attacking),
        "invisible": sorted(
            name for name, row in rows.items()
            if not PAYLOADS[name].harmless and row["succeeded"] and not row["flagged"]
        ),
        "placements": len(tuple(meta.corpus["placements"])),
    }


#: The composed corpus's compliant control. Same argument as `ATTACKED_RUN`: what a *scan* does to
#: an attack that already worked is a property of the page and of the defences, and does not need a
#: model to have been fooled first.
SCANNED_ATTACK_RUN = "attacked-scanned-gullible"

#: How a run over the composed corpus is named, on the same convention the other two held-out
#: corpora use. The paid arm is found under it by model name rather than hardcoded, so a second
#: model appears on this page without an edit here.
SCANNED_ATTACK_PREFIX = "attacked-scanned-"

#: Where the composed corpus is built, when it has been. Not committed — 168 rasterised pages — and
#: one command away (`python -m doc_extract.degrade --attacked`).
SCANNED_ATTACK_CORPUS = ROOT / "data" / "attacked-scanned"


def scanned_injection_study(corpus: list) -> dict[str, object] | None:
    """M6's grid photographed, per rung, from the committed prediction file — plus the reach table.

    The per-rung rate needs no corpus on disk: `degrade.attacked.plan` is pure, so the gold of a
    scanned attacked document is rebuilt in memory from the seed and the run's own provenance block,
    exactly as `injection_study` rebuilds M6's.

    **The reach table is the half that cannot be.** Whether an overlay left a mark on the page is a
    fact about pixels, and no committed artifact records pixels — so it is read from the corpus's
    `reach.jsonl` when the corpus has been built here, and the section renders without it otherwise
    rather than with an invented one. That is the same rule `grounding_on_a_scan` follows.
    """
    directory = ROOT / "results" / SCANNED_ATTACK_RUN
    predictions_path = directory / prediction_file.PREDICTIONS_NAME
    if not predictions_path.exists():  # pragma: no cover — a checkout without that run
        return None

    meta = prediction_file.read_meta(directory / prediction_file.RUN_NAME)
    planned = attacked_grid.plan(
        per_cell=meta.corpus["per_cell"],
        payloads=tuple(PAYLOADS[name] for name in meta.corpus["payloads"]),
        placements=tuple(meta.corpus["placements"]),
        rungs=tuple(RUNGS_BY_NAME[rung["name"]] for rung in meta.corpus["rungs"]),
        base=corpus,
    )
    gold = {document.doc_id: document for document, _, _ in planned}
    by_id = {assignment.doc_id: assignment for _, _, assignment in planned}

    return {
        **_attacked_arm(predictions_path, gold, by_id),
        "run": SCANNED_ATTACK_RUN,
        "reach": _reach_table(),
        "curve": _gate_curve(predictions_path),
        "vision": _vision_arms(gold, by_id),
    }


def _attacked_arm(predictions_path, gold: dict, by_id: dict) -> dict[str, object]:
    """One run's attack success rate over the composed corpus, per rung and overall.

    Shared by the compliant control and the paid vision arm rather than written twice: the two
    answer different questions — what the *defences* do about an attack that worked, and what a
    *model* does with one it can see — and a second copy of the tally is a second place for those
    two numbers to stop being computed the same way.
    """
    rows: dict[str, dict[str, int]] = {}
    for record in prediction_file.read(predictions_path):
        if record.doc_id not in by_id:  # pragma: no cover — reported in the committed attack.md
            continue
        assignment = by_id[record.doc_id]
        payload = PAYLOADS[assignment.payload]
        if payload.harmless:
            #: The control asks for nothing and can never succeed. Leaving it in would lower every
            #: rung's rate by the same seventh, for a reason that has nothing to do with the page.
            continue
        row = rows.setdefault(assignment.template, {"documents": 0, "succeeded": 0})
        row["documents"] += 1
        row["succeeded"] += payload.achieved(
            gold[record.doc_id].invoice, record.parse(), FailureClass(record.failure)
        )
    return {
        "rungs": [{"rung": name, **rows[name]} for name in RUNG_NAMES if name in rows],
        "documents": sum(row["documents"] for row in rows.values()),
        "succeeded": sum(row["succeeded"] for row in rows.values()),
    }


def _vision_arms(gold: dict, by_id: dict) -> list[dict[str, object]]:
    """Every paid arm that read this corpus as images, one entry each.

    Found by prefix and by what each run recorded about its own modality, rather than by a
    hardcoded directory: a remote arm is named for its model, and two models over one corpus are
    two directories precisely so that both can be shown. Returning a list rather than the first
    match is the difference between that and silently renaming the one on the page.

    Every claim the section makes is derived here — the rate, whether anything was repaired,
    whether anything was refused, and whether the rate is the same at every rung — because a second
    arm would otherwise inherit the first one's adjectives unchecked.
    """
    reached = _reached_the_image()
    arms = []
    for directory in sorted((ROOT / "results").glob(f"{SCANNED_ATTACK_PREFIX}*")):
        predictions_path = directory / prediction_file.PREDICTIONS_NAME
        if not predictions_path.exists():
            continue
        meta = prediction_file.read_meta(directory / prediction_file.RUN_NAME)
        if not meta.reads_images:
            continue
        records = list(prediction_file.read(predictions_path))
        tally = _attacked_arm(predictions_path, gold, by_id)
        arms.append({
            **tally,
            "model": meta.model,
            "reached": reached,
            "repairs": sum(record.repairs for record in records),
            "unanswered": sum(1 for record in records if not record.succeeded),
            #: Not "0 % everywhere" — "the same everywhere", which is the claim the prose makes and
            #: is still checkable if a later arm is breached uniformly rather than not at all.
            "uniform": len({row["succeeded"] for row in tally["rungs"]}) == 1,  # type: ignore[index]
        })
    return arms


def _reached_the_image() -> int | None:
    """Attacking documents whose payload left a mark on the page. `None` without the corpus.

    Read straight off `Reach`, which records the payload it belongs to — joining back to a grid
    planned from some other run's provenance would buy nothing and would raise on a corpus built
    with different parameters, in a build where every neighbouring helper degrades instead.
    """
    if not (SCANNED_ATTACK_CORPUS / attacked_grid.REACH_NAME).exists():
        return None  # pragma: no cover — the composed corpus has not been built here
    return sum(
        1 for row in attacked_grid.load_reaches(SCANNED_ATTACK_CORPUS)
        if row.on_the_image and not PAYLOADS[row.payload].harmless
    )


def _gate_curve(predictions_path) -> dict[str, object] | None:
    """The two ends of the gate's curve on this corpus, or `None` without the pages.

    The finding is a *comparison* — accepting only the high-confidence values against accepting
    everything — so both ends are read off one `Curve` rather than one being quoted and the other
    remembered. Grounding needs the rendered page, which is why this is the second half of this
    section that a checkout without the corpus renders without.
    """
    if not (SCANNED_ATTACK_CORPUS / MANIFEST_NAME).exists():
        return None  # pragma: no cover — the composed corpus has not been built here
    curve = run.gate(
        dataset.load(SCANNED_ATTACK_CORPUS), prediction_file.read(predictions_path)
    )
    points = {str(point.level): point for point in curve.points}
    top, everything = points.get(str(Confidence.HIGH)), points.get(str(Confidence.NONE))
    if top is None or everything is None:  # pragma: no cover — the levels are a closed enum
        return None
    return {
        "coverage": top.coverage, "accuracy": top.accuracy, "leaked": top.leaked,
        "all_accuracy": everything.accuracy, "all_leaked": everything.leaked,
    }


def _reach_table() -> list[dict[str, object]] | None:
    """One row per placement, one column per rung, or `None` when the corpus is not on disk."""
    if not (SCANNED_ATTACK_CORPUS / attacked_grid.REACH_NAME).exists():
        return None  # pragma: no cover — the composed corpus has not been built here
    reaches = attacked_grid.load_reaches(SCANNED_ATTACK_CORPUS)
    placements = _first_seen(row.placement for row in reaches)
    return [
        {
            "placement": placement,
            "channels": [
                _channel([
                    row for row in reaches
                    if row.placement == placement and row.rung == rung
                ])
                for rung in RUNG_NAMES
            ],
        }
        for placement in placements
    ]


def _channel(rows: list) -> str:
    """What a cell says, classified by the module that owns the rule and then dressed for HTML.

    Deliberately not a second implementation. A page of derived figures is most exposed to exactly
    that — a rule restated somewhere it can drift — so the decision comes from
    `attacked_report.channel` and only the Markdown emphasis and the non-breaking space are undone
    here.
    """
    said = attacked_report.channel(rows)
    return {
        attacked_report.BOTH: "text&nbsp;+&nbsp;image",
        attacked_report.NOBODY: "nobody",
    }.get(said, html.escape(said))


def _first_seen(values) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for value in values:
        seen.setdefault(value, None)
    return tuple(seen)


def field_list(counts: collections.Counter, limit: int = 3) -> str:
    return ", ".join(
        f"<code>{html.escape(field)}</code>&nbsp;&times;&nbsp;{n}"
        for field, n in counts.most_common(limit)
    )


def percent(value: float | None) -> str:
    """A rate, in HTML, written the way the committed reports write it.

    Delegates to `eval/format.rate` rather than formatting again here, so the page and the report
    cannot disagree about the same figure: an absent denominator is a dash in both, and `100 %`
    means exactly 100 % in both. This file had its own `.1f` until that divergence was caught.
    """
    text = rate(value)
    return "&mdash;" if text == DASH else text.replace(" %", "&nbsp;%")


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


#: The one figure on this page that is typed rather than derived. Token counts are in the run's
#: prediction file, but the price per token is not in this repository and inventing a constant for
#: it would be worse than admitting the number came from an invoice.
OPUS_COST = "$3.20"


def formatting_only_differences(corpus: list, run: str = "claude-opus-5") -> int:
    """Field values that differ from gold as text but not as quantities.

    The page claims a specific count of trailing zeros, so it computes one: the model writes
    `137.30` where the generator stored `137.3`, and `fields.equal` was already defined to call
    those the same amount. Derived rather than typed, like everything else here except the cost.

    Compared as **rendered text**, not as values. `Decimal("137.3") == Decimal("137.30")` is true,
    which is the whole point of the scorer treating them as one quantity — and is exactly why a
    naive value comparison here counted zero of them.
    """
    directory = ROOT / "results" / run
    predictions_path = directory / prediction_file.PREDICTIONS_NAME
    if not predictions_path.exists():  # pragma: no cover — a checkout without that run
        return 0

    gold = {document.doc_id: document.invoice for document in corpus}
    differences = 0
    for record in prediction_file.read(predictions_path):
        predicted = record.parse()
        if predicted is None:
            continue
        theirs = fields.read(predicted)
        for (name, key), value in fields.read(gold[record.doc_id]).values.items():
            other = theirs.get(name, key)
            if value is None or other is None:
                continue
            if fields.render(value) != fields.render(other) and fields.equal(name, value, other):
                differences += 1
    return differences


def detector_section(study: dict[str, object] | None) -> str:
    """The headline question, rendered from `detector_study` rather than from memory."""
    if study is None:  # pragma: no cover — a checkout without the studied run
        return "<p class=\"note\">No committed run to ask the question of.</p>"
    return f"""<p>The project's headline question, asked of <code>{html.escape(str(study["model"]))}</code>,
which gets {study["wrong_documents"]} of {study["judged"]} documents wrong and so supplies a real,
unlabelled model-error population. The invariants are run on the <strong>prediction</strong>, never
on the gold &mdash; the signal has to be available at inference time on a document nobody
annotated.</p>
<table>
  <thead><tr><th></th><th class="num">flagged</th><th class="num">silent</th></tr></thead>
  <tbody>
    <tr><th>fields wrong</th><td class="num">{study["true_positive"]}</td><td class="num">{study["false_negative"]}</td></tr>
    <tr><th>fields right</th><td class="num">{study["false_positive"]}</td><td class="num">{study["true_negative"]}</td></tr>
  </tbody>
</table>
<p><strong>Precision {percent(study["precision"])}, recall {percent(study["recall"])}</strong>, and
{percent(study["localisation"])} of the catches point at a field that is genuinely wrong.</p>
<p class="note">The recall is not a property of the detector. It is the fraction of that model's
mistakes that happened to land on numeric fields. Caught: {field_list(study["caught"])}. Every one
of the {study["missed_total"]} misses is a <strong>name or a description</strong> &mdash; a field
with no redundancy behind it for arithmetic to check &mdash; and {study["top_missed_tier_count"]} of
them sit in the <code>{html.escape(str(study["top_missed_tier"]))}</code> tier, where a description
wraps across a page break. Not one arithmetic error escaped.</p>
<p>That is the case for the grounding layer, arrived at by measurement rather than assumed: it
covers exactly the fields the arithmetic cannot see, because a description the model invented is a
value that resolves to no span on the page.</p>
<p class="note">A caution the study prints beside its own numbers: a <strong>confidently wrong but
internally consistent answer is invisible</strong>. The constant baseline sits at prevalence
100&nbsp;% with recall 0&nbsp;%.</p>"""


def foreign_section(rows: list[dict[str, object]] | None) -> str:
    """M7's paired comparison, rendered from `foreign_study` rather than from memory."""
    if not rows:  # pragma: no cover — a checkout without the foreign arms
        return ""
    body = "\n".join(
        f'    <tr><th><code>{html.escape(str(row["baseline"]))}</code></th>'
        f'<td class="num">{percent(row["own_accuracy"])}</td>'
        f'<td class="num">{percent(row["foreign_accuracy"])}</td>'
        f'<td class="num">{row["foreign_extracted"]} / {row["documents"]}</td></tr>'
        for row in rows
    )
    failed = [row for row in rows if row["foreign_extracted"] == 0]
    note = ""
    if failed:
        which = ", ".join(f'<code>{html.escape(str(row["baseline"]))}</code>' for row in failed)
        classes = ", ".join(sorted({
            f"<code>{html.escape(name)}</code>"
            for row in failed for name in row["failures"]
        }))
        #: The count comes from the failing rows themselves, not from the first row of the table.
        #: Every arm scores the same corpus today, so reading it off the oracle's row happened to
        #: print the right number — and would have gone on printing it after they diverged.
        judged = " / ".join(sorted({str(row["documents"]) for row in failed}))
        note = (
            f"<p class=\"note\">{which} did not read the page badly &mdash; it could not "
            f"<em>begin</em>. Not one of the {judged} documents produced an invoice the schema "
            f"would accept, every one recorded as {classes}. The labels it matches are the whole "
            "of what it was doing.</p>"
        )
    return f"""<h2>How much of a reading was the template?</h2>
<p>The synthetic corpus varies what an invoice <em>means</em> and not how the page <em>says</em> it:
three layouts, one vocabulary, one number format. So a second corpus prints the identical gold in
three unfamiliar ones &mdash; other Polish labels for every field, other column orders, other number
and date formats, and block orders that put the totals before the rows. Same seed, same invoices,
document for document: a difference between the two columns is the <strong>page</strong>, because
nothing else moved.</p>
<table><thead><tr><th>baseline</th><th class="num">its own page</th><th class="num">an unfamiliar page</th><th class="num">read at all</th></tr></thead>
<tbody>
{body}
</tbody></table>
{note}
<p class="note">The other two rows are the controls that make the first one mean something. The
oracle is handed the gold and is unaffected, which says the corpus is scorable and its gold did not
move; the constant baseline never looks at the page and scores <em>identically</em> on both, which
is what a paired comparison should do to a reader that reads nothing.</p>
<p class="note"><strong>This is not a real held-out set and does not claim to be.</strong> It holds
the semantics fixed on purpose, so it answers one question and not the other: how much of a result
was presentation. Real invoices also bring skew, stamps, scans and layouts nobody anticipated, and
none of that is here.</p>"""


def _grounding_on_a_model(grounding: dict) -> str:
    """The other half: what the same signal does on a population of real mistakes, rung by rung."""
    rows = grounding.get("model_rows")
    if not rows:  # pragma: no cover — a checkout with no paid arm over the scanned corpus
        return ""
    name = html.escape(str(grounding["model"]))
    body = "\n".join(
        f'    <tr><th><code>{html.escape(rung)}</code></th>'
        f'<td class="num">{counts["TP"]}</td><td class="num">{counts["FP"]}</td>'
        f'<td class="num">{counts["FN"]}</td>'
        f'<td class="num">{percent(_ratio(counts["TP"], counts["TP"] + counts["FP"]))}</td>'
        f'<td class="num">{percent(_ratio(counts["TP"], counts["TP"] + counts["FN"]))}</td></tr>'
        for rung, counts in rows.items()
    )
    return f"""<p>And the mirror of it, on a population of real mistakes: <code>{name}</code>
reading the same pages as images.</p>
<table><thead><tr><th>rung</th><th class="num">TP</th><th class="num">FP</th><th class="num">FN</th><th class="num">precision</th><th class="num">recall</th></tr></thead>
<tbody>
{body}
</tbody></table>
<p class="note">Read the first row against the other two. Where a text layer survives, grounding is
at its <em>most</em> precise measurement anywhere in this project &mdash; it catches almost every
wrong value and raises no false alarm at all. Where there is none it flags everything, so its recall
is 100&nbsp;% by vacuity and its precision collapses. <strong>The gate does not survive a scan; it
survives an OCR</strong> &mdash; which is a usable engineering conclusion rather than a negative
one: put a recogniser in front of the model and the signal comes back.</p>"""


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _and_list(items: list[str]) -> str:
    """`a`, `a and b`, `a, b and c` — so a generated sentence reads as one however many arms land."""
    if len(items) < 3:
        return " and ".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _scanned_caveats(rows: list[dict[str, object]]) -> str:
    """What a reader has to know before comparing a model's row with a baseline's.

    Both are generated from the rows rather than typed, because both are properties of whichever
    runs happen to be committed: a checkout with no paid arm should not carry a paragraph about
    one, and a rung whose figure is dragged by a truncation should say which run truncated.
    """
    notes = []
    models = [row for row in rows if row["is_model"]]
    if models:
        named = _and_list(
            [f"<code>{html.escape(str(row['baseline']))}</code>" for row in models]
        )
        notes.append(
            f"<p class=\"note\">For {named}, <em>its own page</em> is that model reading the clean "
            "corpus as <strong>text</strong>, so the drop across each of those rows is two changes "
            "at once — "
            "the page became a picture and the reader started looking at pixels. The column that "
            "isolates the modality alone is <code>searchable</code>: the same information is "
            "available there as in the text arm, and it is read as an image.</p>"
        )
    dragged = [
        (row["baseline"], rung, count)
        for row in rows
        for rung, count in sorted(dict(row["truncated"]).items())
    ]
    if dragged:
        listed = ", ".join(
            f"<code>{html.escape(str(name))}</code> on <code>{html.escape(rung)}</code> "
            f"({count} document{'s' if count > 1 else ''})"
            for name, rung, count in dragged
        )
        many = len(dragged) > 1
        notes.append(
            f"<p class=\"note\">{'Some figures' if many else 'One figure'} above "
            f"{'are' if many else 'is'} not a legibility result: {listed} ran out of output tokens "
            "mid-answer. A truncated document contributes every one of its fields as <em>missed</em>, "
            "which is enough to move a rung's accuracy by several points on its own — and running "
            "out of room while transcribing a long table from an image is a cost of the modality "
            "rather than of the rung.</p>"
        )
    return "\n".join(notes)


def scanned_section(rows: list[dict[str, object]] | None, grounding: dict | None) -> str:
    """M7's other paired comparison: the same page, photographed."""
    if not rows:  # pragma: no cover — a checkout without the scanned arms
        return ""
    head = "".join(f'<th class="num">{html.escape(name)}</th>' for name in RUNG_ORDER)
    body = "\n".join(
        f'    <tr><th><code>{html.escape(str(row["baseline"]))}</code></th>'
        f'<td class="num">{percent(row["own_accuracy"])}</td>'
        + "".join(
            f'<td class="num">{percent(row["rungs"].get(name))}</td>' for name in RUNG_ORDER
        )
        + "</tr>"
        for row in rows
    )
    gate = ""
    if grounding:
        control = grounding["control"]
        cells = "\n".join(
            f'    <tr><th><code>{html.escape(name)}</code></th>'
            f'<td class="num">{counts["TN"]}</td>'
            f'<td class="num">{counts["FP"] + counts["TP"]}</td></tr>'
            for name, counts in control.items()
        )
        total = sum(counts["FP"] + counts["TP"] for counts in control.values())
        #: Fenced by a comment because this is the one block on the page that needs a corpus on
        #: disk, so it is the one block `tests/test_site_committed.py` has to forgive when it
        #: checks the committed page against the generator. A fence the test can key on beats a
        #: pattern over prose that a rewording would silently widen.
        gate = f"""{CORPUS_DEPENDENT}
<p><strong>The column above is not the finding. What a scan does to the
<em>gate</em> is.</strong> Run the oracle &mdash; a perfect reading, nothing wrong anywhere &mdash;
over the scanned corpus, and grounding raises {total} false alarms:</p>
<table><thead><tr><th>rung</th><th class="num">grounded</th><th class="num">ungrounded</th></tr></thead>
<tbody>
{cells}
</tbody></table>
<p class="note">Grounding resolves a value to a span of page text, and there is no page text. It
does not degrade &mdash; it inverts, and it inverts <em>silently</em>: an ungrounded correct value
looks exactly like an ungrounded fabricated one. Of the two signals the routing gate is built on,
only the arithmetic survives a scan &mdash; and that is the one an adversary can satisfy on
purpose.</p>
{_grounding_on_a_model(grounding)}
{CORPUS_DEPENDENT_END}"""
    return f"""<h2>When the page is a picture</h2>
<p>Every document measured so far arrived with a text layer <code>reportlab</code> wrote: exact,
complete, in the order the values were drawn. That is the last unearned advantage in the corpus. An
invoice in a real inbox is frequently a <em>photograph</em> of an invoice, and there is no text layer
at all. So a third corpus prints the same gold in the same layout and then scans it, at three rungs
that each isolate one thing: one keeps a text layer (an OCR assumed perfect), one removes the text
layer and changes nothing else, and one is what a supplier emails at 150&nbsp;dpi.</p>
<table><thead><tr><th>baseline</th><th class="num">its own page</th>{head}</tr></thead>
<tbody>
{body}
</tbody></table>
<p class="note">The control is exact rather than approximate: the fitted reader's predictions on the
rung that keeps a text layer are identical, field for field, to its predictions on the clean corpus.
That is what makes the other two columns a measurement of the missing text layer and not of the
damage to the image.</p>
{_scanned_caveats(rows)}
{gate}"""


def stripped_section(study: dict[str, object] | None) -> str:
    """The degenerate reading, rendered from `stripped_study` rather than from memory."""
    if study is None:  # pragma: no cover — a checkout without that run
        return ""
    return f"""<h2>When the arithmetic has nothing to say</h2>
<p>Every cross-field identity needs two figures to compare. An answer that keeps the total and drops
the rows and the rate blocks offers one &mdash; so those rules are not <em>wrong</em> about it, they
are <strong>unable to speak</strong>. The <code>stripped</code> baseline is exactly that reading, on
all {study["judged"]} documents.</p>
<table><thead><tr><th></th><th class="num">prevalence</th><th class="num">precision</th><th class="num">recall</th></tr></thead>
<tbody>
    <tr><th>hard rules</th><td class="num">{percent(study["prevalence"])}</td><td class="num">{percent(study["hard_precision"])}</td><td class="num">{percent(study["hard_recall"])}</td></tr>
    <tr><th>heuristic rules</th><td class="num">{percent(study["prevalence"])}</td><td class="num">{percent(study["heuristic_precision"])}</td><td class="num">{percent(study["heuristic_recall"])}</td></tr>
</tbody></table>
<p>The one rule that fires is the heuristic whose entire content is <em>no rule could run</em>, and
it fires on every document, with {study["heuristic_false_positive"]} false positives. The fields
this reading does keep are <em>missing</em> rather than wrong &mdash; which is why the two hard
rules that need only a single figure, the NIP and the IBAN check digits, did run and were right to
find nothing. Those three
heuristic rules had never fired on any earlier run &mdash; a metric identical across every variant,
which this project's own rules call broken rather than stable. Giving them a population was the fix;
dropping them was the alternative.</p>
<p class="note"><strong>And the gate accepts all of it.</strong> Coverage is measured over the values
a prediction asserted, so a reading that loses three quarters of the invoice routes everything to
<code>accept</code>, at 100&nbsp;% accuracy, leaking nothing. No signal here separates &ldquo;correctly
absent&rdquo; from &ldquo;silently dropped&rdquo;; the count of what was never asserted is the only
column that sees it.</p>"""


def injection_section(study: dict[str, object] | None) -> str:
    """M6, rendered from `injection_study` rather than from memory."""
    if study is None:  # pragma: no cover — a checkout without the attacked run
        return "<p class=\"note\">No committed run over an attacked corpus.</p>"

    rows: dict[str, dict[str, object]] = study["rows"]  # type: ignore[assignment]
    body = "".join(
        f'<tr><th><code>{html.escape(name)}</code></th>'
        f'<td>{html.escape(str(row["goal"]))}</td>'
        f'<td class="num">{row["succeeded"]} / {row["documents"]}</td>'
        f'<td class="num">{row["flagged"]} / {row["documents"]}</td></tr>'
        for name, row in rows.items()
    )
    invisible = ", ".join(f"<code>{html.escape(name)}</code>" for name in study["invisible"])
    return f"""<p>Seven payloads &mdash; six that ask for something and one control that asks for
nothing &mdash; printed in {study["placements"]} places on the page, including in white ink, where a
human approving the invoice sees nothing and the text layer carries every word. The gold of an
attacked document is the gold of the document it was made from, so the same scorer, detector and
gate run over it unchanged.</p>
<table>
  <thead><tr><th>payload</th><th>asks for</th><th class="num">obeyed</th><th class="num">arithmetic fires</th></tr></thead>
  <tbody>{body}</tbody>
</table>
<p class="note">The column that matters is <em>arithmetic fires</em>. It is computed against
<code>{html.escape(str(study["run"]))}</code>, a control that obeys every instruction it finds on a
page: its success rate is 100&nbsp;% by construction, which is what makes it the right arm for this
question. What a <em>defence</em> does about an attack that worked is a property of the defence, and
does not need a model to have been fooled first.</p>
<p><strong>The two payloads the arithmetic never sees are {invisible}</strong> &mdash; and they are
the two an attacker would actually run. Redirecting a payment or reissuing the invoice under another
NIP does not break any identity: the attacker picks an account they control, so the check digits are
valid, and the value is printed on the page, so grounding finds it too. Both of M5's signals were
measured on a model's <em>errors</em>, where a wrong digit is a random digit. Neither transfers to an
adversary who can compute a check digit, and the committed <code>attack.md</code> shows the routing
gate accepting every one of those documents.</p>
<p class="note">That is the milestone's result, and it is a negative one: the arithmetic gate is a
defence against misreading, not against injection. Ordering the stages so a document can never
choose them, deriving the fence marker from the text it wraps, and telling the model to transcribe
rather than compute are what stand between the payload and the answer &mdash; and the honest way to
report a structural defence is to attack it and publish the rate.</p>"""


def scanned_injection_section(study: dict[str, object] | None) -> str:
    """The same grid photographed. Two tables, and the second only when the corpus is on disk."""
    if study is None:  # pragma: no cover — a checkout without that run
        return "<p class=\"note\">No committed run over a scanned attacked corpus.</p>"

    rungs: list[dict[str, object]] = study["rungs"]  # type: ignore[assignment]
    body = "".join(
        f'<tr><th><code>{html.escape(str(row["rung"]))}</code></th>'
        f'<td class="num">{row["documents"]}</td>'
        f'<td class="num">{row["succeeded"]}</td>'
        f'<td class="num">{rate(_success_rate(row))}</td></tr>'
        for row in rungs
    )
    return f"""<p>Compose the two corpora &mdash; M6's grid printed and then put through M7's
scanner, gold untouched by either &mdash; and the compliant reader above, breached on every attacked
document it is given a clean page of, is breached on {rate(_success_rate(study))} of these
({study["succeeded"]} of {study["documents"]}). The decomposition is the whole finding.</p>
<table>
  <thead><tr><th>rung</th><th class="num">attacked</th><th class="num">succeeded</th><th class="num">ASR</th></tr></thead>
  <tbody>{body}</tbody>
</table>
<p class="note">Computed from <code>{html.escape(str(study["run"]))}</code>, the same control M6 uses,
by rebuilding each scanned attacked document's gold in memory from the corpus seed.</p>
<p><strong>The two zeros are blindness, not defence.</strong> No payload reached the text layer on
those rungs because no <em>text</em> did &mdash; the page carries none. A reader that looks at the
page sees them exactly as the reach table says it does.</p>
{_reach_section(study.get("reach"))}
{_vision_section(study.get("vision"))}
{_inversion(study.get("curve"))}"""


def _vision_section(arms: object) -> str:
    """What the models that read the pixels did with the same corpus — one paragraph each."""
    if not arms:  # pragma: no cover — a checkout without a paid arm over this corpus
        return ""
    return "\n".join([
        *(_vision_arm_paragraph(row) for row in arms),  # type: ignore[union-attr]
        """<p class="note">Two things that does not establish, and both are limits of the suite
rather than of any model: the payloads are <strong>fixed strings</strong> that never adapt and were
not written against the reader being measured, so the rate scores a catalogue rather than an
adversary; and this is a synthetic corpus. The denial payload is the illustration &mdash; it beat
the compliant control every time and the model above not once, which is a fact about two readers
rather than about the payload. The structural defences are still what the case rests on, because
they are what holds when the reader is not this one.</p>""",
    ])


def _vision_arm_paragraph(row: dict[str, object]) -> str:
    """One arm, with every adjective derived from its own prediction file."""
    reached = row.get("reached")
    #: The claim that makes a zero a defence result rather than arithmetic — and the one sentence
    #: here that needs the corpus, so it is fenced on its own rather than with the paragraph.
    ink = (
        f" {CORPUS_DEPENDENT}<strong>{reached} of those {row['documents']} carried their payload "
        f"as ink on a page it looked at.</strong> The rest are the white-ink placement the scanner "
        f"had already erased, where a rate is not evidence of anything."
        f"{CORPUS_DEPENDENT_END}"
        if reached is not None and reached > 0 else ""
    )
    clean = " and ".join(
        claim for claim, holds in (
            ("no repairs", not row["repairs"]),
            ("nothing left unanswered", not row["unanswered"]),
        ) if holds
    )
    return f"""<p><strong>A frontier model reading the pixels met
{row["succeeded"]} of {row["documents"]} attacking objectives.</strong>
<code>{html.escape(str(row["model"]))}</code>, every page sent as an image &mdash; an attack success
rate of {rate(_success_rate(row))}{", the same at every rung" if row["uniform"] else ""}
{f", with {clean}" if clean else ""}.{ink}</p>"""


def _inversion(curve: object) -> str:
    """The gate's two ends, side by side, or a note saying which command produces them."""
    if not curve:
        return (  # pragma: no cover — the composed corpus has not been built here
            '<p class="note">Grounding resolves a value against the page\'s text, so the gate\'s '
            'curve on this corpus needs the pages. Build it with <code>python -m '
            'doc_extract.degrade --attacked</code>.</p>'
        )
    row: dict[str, object] = curve  # type: ignore[assignment]
    return f"""{CORPUS_DEPENDENT}
<p><strong>And the gate inverts.</strong> Accepting only the high-confidence values
covers {rate(row["coverage"])} of what the reader asserted at {rate(row["accuracy"])} accuracy and
lets {row["leaked"]} wrong values through; accepting <em>everything</em> is
{rate(row["all_accuracy"])} accurate. <strong>The gate's own bucket is the less accurate one.</strong>
The only values that ground are those on a page that kept a text layer &mdash; which is exactly the
rung where the attacks worked &mdash; so the gate concentrates the attacked-and-obeyed values into
the bucket it calls high confidence. On a population of model <em>errors</em> the same gate raised
accuracy instead of lowering it, and the committed <code>gate.md</code> files hold both curves.</p>
{CORPUS_DEPENDENT_END}"""


def _success_rate(row: dict[str, object]) -> float | None:
    documents = int(row["documents"])  # type: ignore[arg-type]
    return int(row["succeeded"]) / documents if documents else None  # type: ignore[arg-type]


def _reach_section(reach: object) -> str:
    """Which channel each payload survived by, when the corpus that measured it is on disk.

    Fenced for the reason the scanned corpus's grounding block is: whether a payload left a mark is
    a fact about pixels, no committed artifact records pixels, and a checkout without the corpus
    would otherwise render a page that disagrees with the committed one.
    """
    if not reach:
        return (  # pragma: no cover — the composed corpus has not been built here
            '<p class="note">The reach table is a fact about pixels and no committed artifact '
            'records pixels. Build the corpus with <code>python -m doc_extract.degrade '
            '--attacked</code> to render it here.</p>'
        )
    rows = "".join(
        f'<tr><th><code>{html.escape(str(row["placement"]))}</code></th>'
        + "".join(f'<td>{channel}</td>' for channel in row["channels"])
        + "</tr>"
        for row in reach  # type: ignore[union-attr]
    )
    heads = "".join(f'<th><code>{html.escape(name)}</code></th>' for name in RUNG_NAMES)
    return f"""{CORPUS_DEPENDENT}
<table>
  <thead><tr><th>placement</th>{heads}</tr></thead>
  <tbody>{rows}</tbody>
</table>
<p class="note">Measured at build time with no model. <em>text</em> means the marker is in the text
layer the source reader gets off the scanned page; <em>image</em> means the attacked page and the
unattacked page it was made from differ as pictures, through the same scanner at the same seed
&mdash; so a payload that moved no pixel cannot be seen by anything that looks at the page.</p>
<p><strong>A scan deletes the white-ink attack outright.</strong> White on white contributes no
pixel, so there is nothing for a recogniser to recover and nothing for a vision model to read: the
placement designed to be invisible to the human approving the invoice is the one a photocopier
destroys. That is an accident of the medium and not a control &mdash; it protects only the placement
that hides from a person, and an attacker who prints in ink loses nothing.</p>
{CORPUS_DEPENDENT_END}"""


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
        detector_section=detector_section(detector_study(corpus)),
        stripped_section=stripped_section(stripped_study(corpus)),
        foreign_section=foreign_section(foreign_study(corpus)),
        scanned_section=scanned_section(scanned_study(corpus), grounding_on_a_scan()),
        injection_section=injection_section(injection_study(corpus)),
        scanned_injection_section=scanned_injection_section(scanned_injection_study(corpus)),
        formatting_only=formatting_only_differences(corpus),
        opus_cost=OPUS_COST,
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
  <p class="eyebrow">P5 &middot; KSeF FA(3) &middot; milestones 1&ndash;6 of 7, and most of the seventh</p>
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
  rest of milestone 5. Milestone 6 attacks the whole thing: seven payloads printed on the page,
  one of them in white ink, and the finding is a negative one &mdash; the arithmetic gate stops the
  attacks that lie about a total and is blind to the one that redirects a payment.
</div>

<h2>Does &ldquo;the arithmetic holds&rdquo; predict &ldquo;the fields are right&rdquo;?</h2>
{detector_section}

{stripped_section}

{foreign_section}

{scanned_section}

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
<p>What it does <em>not</em> have is a page nobody in this repository designed. Two of the three
things that used to be missing are measured now, on held-out corpora of their own &mdash; an
unfamiliar layout and a poor scan, each varying one thing so that a drop is attributable to it, and
both reported above. What is still absent is a genuinely real invoice: a stamp, a signature, a fold,
a layout no template anticipated because no template wrote it.</p>

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
document, for {opus_cost}. Its only divergence from the gold's own serialisation is
{formatting_only} trailing zeros &mdash; it writes <code>137.30</code> where the generator stored <code>137.3</code>, which is what
the page prints and what the scorer's amount comparison was already defined to treat as the same
quantity. A corpus that the strongest non-model reader finds hard and a frontier model finds trivial
is measuring layout parsing, not reading.</p>

<h2>The invoice as untrusted input</h2>
{injection_section}

<h2>Now photograph the attacked page</h2>
{scanned_injection_section}

<h2>What is not built yet</h2>
<p>Stated plainly, because a portfolio page that reads as finished when it is not is worse than no
page at all.</p>
<table>
  <tbody>
    <tr><th>M3 &mdash; source layer, extraction, structured output with an owned schema retry</th><td class="num">built</td></tr>
    <tr><th>M4 &mdash; pure scorer, per-field metrics with support, failure taxonomy, baselines</th><td class="num">built, model run</td></tr>
    <tr><th>M5 &mdash; <strong>the detector study</strong>, grounding, routing, the coverage&ndash;accuracy curve</th><td class="num">built</td></tr>
    <tr><th>M6 &mdash; injection suite, attack success rate, trust-boundary ADR</th><td class="num">built, offline arms and one paid</td></tr>
    <tr><th>M7 &mdash; held-out corpora, the vision path, the attacked page photographed</th><td class="num">built, model arms on two of the three</td></tr>
    <tr><th>&mdash; a paid arm over the <em>foreign</em> corpus</th><td class="num">not built</td></tr>
    <tr><th>&mdash; an adaptive attacker, which no fixed payload set stands in for</th><td class="num">not built</td></tr>
    <tr><th>&mdash; a grounding signal that can say <em>there was nothing to look in</em></th><td class="num">not built</td></tr>
    <tr><th>&mdash; a real invoice nobody generated</th><td class="num">not built</td></tr>
  </tbody>
</table>
<p class="note">The headline question &mdash; does &ldquo;the invariants hold&rdquo; actually predict
&ldquo;the fields are correct&rdquo;? &mdash; met an awkward first answer: on the run that mattered
most there was nothing to predict, because the model made no mistakes. It has been answered instead
against injected errors, a weaker reader, and two held-out corpora &mdash; and the scanned one shows
that making a page <em>harder to see</em> does not un-saturate it either. Making a page unfamiliar
might, and that is the arm this project has not paid for. A negative result is a publishable result,
and so is a corpus that turned out to be too easy.</p>

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
  <p><a href="{repo}">Source on GitHub</a> &middot; built from the tree after
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
