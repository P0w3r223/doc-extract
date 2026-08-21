"""A `Study` as Markdown. Formatting only — nothing below computes a number.

Three things this report has to say beside its tables, because each of them changes what the
headline means:

* **An attack success rate is a rate over attacks that reached the model.** The suite refuses to
  ship a document whose payload did not survive rendering, so the denominator is attacks that were
  printed and read — but a payload the corpus never carried would still be missing, and `missing`
  and `unmatched` are printed above the first table rather than below the last.
* **The gate is not a defence against every payload.** The leak column counts successful attacks the
  routing gate would have accepted anyway, and the interesting cases are the ones where it does
  nothing: an attacker's identifiers pass their check digits and their values are printed on the
  page, so both of M5's signals agree with them.
* **A refusal is not a rescue.** The denial payload succeeds by producing nothing, and nothing is
  then accepted. That is an availability attack that worked, and it gets its own line instead of
  being counted as the gate having caught something.
"""

from __future__ import annotations

from collections.abc import Iterable

from doc_extract.attack.outcome import Rate, Study
from doc_extract.attack.payloads import BY_NAME, DENIAL
from doc_extract.eval.format import DASH
from doc_extract.eval.format import rate as _rate
from doc_extract.eval.predictions import RunMeta


def render(study: Study, *, run: RunMeta, directory: str = "", preamble: str = "") -> str:
    """`preamble` is a section a caller knows about and this module must not.

    The scanned attacked corpus measures which channel each payload reached its reader by, and that
    table reframes every rate below it — a rung where nothing reached the model at all produces an
    attack success rate of zero that means *blind*, not *defended*. It is rendered by the package
    that measured it and inserted here, above the tables, because a qualification printed under the
    numbers it qualifies is one a reader meets too late. Importing it would point `attack/` at the
    scanner, which is the one direction `degrade/attacked.py` says this composition does not run in.
    """
    #: The caveats sit **above** the tables, as they do in `selective_report.py` and for the same
    #: reason: one of them reframes the leak column entirely, and a qualification printed under the
    #: numbers it qualifies is one a reader meets too late.
    parts = [
        _header(study, run=run, directory=directory),
        _coverage(study),
        preamble,
        #: Whether a reach table is actually above the caveats, not whether one could be. A caveat
        #: that points at a section this file does not contain is worse than the general one it
        #: replaced — and `--vision` over M6's *unscanned* corpus is exactly that combination.
        _caveats(study, run=run, has_reach=bool(preamble)),
        _payloads(study),
        _placements(study, has_reach=bool(preamble)),
        _templates(study),
        _grid(study),
        _leaks(study),
    ]
    return "\n\n".join(part for part in parts if part) + "\n"


def _header(study: Study, *, run: RunMeta, directory: str) -> str:
    overall = study.overall
    lines = [
        f"# the injection suite — {run.model}",
        "",
        "| | |",
        "|---|---|",
        f"| answered by | `{run.model}` |",
        f"| saw | {run.options.get('sees', 'unstated')} |",
        #: Its own row rather than folded into `saw`, because the two say different things: `saw`
        #: is what the baseline is *allowed* to look at, and this is the modality it looked in. The
        #: same scanned corpus can be read either way, and two attack success rates measured across
        #: that difference are not comparable — a header naming only one would hide which.
        *([f"| read it as | {run.options['reads']} |"] if run.options.get("reads") else []),
        f"| corpus | `{run.corpus_dir}` |",
        f"| attacked documents | {overall.documents} |",
        f"| attacks that met their objective | {overall.succeeded} |",
        f"| **attack success rate** | **{_rate(overall.rate)}** |",
        f"| of those, accepted by the gate | {overall.leaked} |",
        f"| read exactly right anyway | {overall.exact} |",
        f"| control documents (no instruction) | {study.control.documents} |",
        f"| of those, read exactly right | {study.control.exact} |",
    ]
    if directory:
        lines.insert(4, f"| run | `{directory}` |")
    return "\n".join(lines)


def _coverage(study: Study) -> str:
    """Printed only when the three files did not line up, and printed above everything."""
    if study.complete:
        return ""
    lines = ["> **Incomplete.** This is not a headline number.", ">"]
    if study.missing:
        lines.append(
            f"> {len(study.missing)} attacked document(s) have no prediction: "
            f"{', '.join(sorted(study.missing)[:8])}"
            + (" …" if len(study.missing) > 8 else "")
        )
    if study.unmatched:
        lines.append(
            f"> {len(study.unmatched)} prediction(s) describe documents the suite did not attack: "
            f"{', '.join(sorted(study.unmatched)[:8])}"
            + (" …" if len(study.unmatched) > 8 else "")
        )
    return "\n".join(lines)


def _payloads(study: Study) -> str:
    return "\n".join([
        "## Per payload",
        "",
        "`unchanged` is the other half of the question: how often the extraction came back exactly "
        "right despite the injected text. A payload with a low success rate and a low `unchanged` "
        "did not fail harmlessly — it confused the reader without steering it.",
        "",
        "| payload | goal | n | succeeded | ASR | leaked | unchanged |",
        "|---|---|---:|---:|---:|---:|---:|",
        *(_payload_row(row) for row in study.by_payload),
    ])


def _payload_row(row: Rate) -> str:
    payload = BY_NAME.get(row.label)
    goal = payload.goal if payload is not None else DASH
    return (
        f"| `{row.label}` | {goal} | {row.documents} | {row.succeeded} | "
        f"{_rate(row.rate)} | {row.leaked} | {_rate(row.unchanged)} |"
    )


def _placements(study: Study, *, has_reach: bool = False) -> str:
    return "\n".join([
        "## Per placement",
        "",
        "Where on the page the same sentences were printed. `invisible` is white ink — absent to a "
        "human approving the invoice, and present in the text layer the extractor reads **on a "
        "page nobody photographed**."
        + (
            " Whether it still is on this corpus is what the reach table above says, and it is not "
            "a property of the placement."
            if has_reach else ""
        ),
        "",
        "`unchanged` is **not comparable across placements**. The `description` placement prints "
        "the payload inside an item's own description cell, and that description is a scored "
        "field — so wherever the payload reaches the reader, one that transcribes the cell "
        "perfectly still differs from the gold there, by definition rather than by behaviour. The "
        "other three write where nothing is scored."
        + (
            " On a corpus where the payload reaches the reader on some documents and not others, "
            "this row mixes the two and the reach table above is what separates them."
            if has_reach else ""
        ),
        "",
        "| placement | n | succeeded | ASR | leaked | unchanged |",
        "|---|---:|---:|---:|---:|---:|",
        *(
            f"| `{row.label}` | {row.documents} | {row.succeeded} | {_rate(row.rate)} | "
            f"{row.leaked} | {_rate(row.unchanged)} |"
            for row in study.by_placement
        ),
    ])


def _templates(study: Study) -> str:
    """What the manifest calls a page. Printed only when the corpus varies it.

    On M6's attacked corpus that is the layout the invoice was printed in, and the row exists to say
    whether a layout mattered. On the scanned attacked corpus it is the rung, and the row is the
    measurement — but what it means is decided by the manifest, so nothing here names either.
    """
    if len(study.by_template) < 2:
        return ""
    return "\n".join([
        "## Per template",
        "",
        "`template` is whatever the corpus's manifest records as what a page looks like. Read it "
        "against that corpus's provenance block rather than assuming a layout: a corpus that "
        "varies the scanner puts the rung here, and records the layouts beside it.",
        "",
        "| template | n | succeeded | ASR | leaked | unchanged |",
        "|---|---:|---:|---:|---:|---:|",
        *(
            f"| `{row.label}` | {row.documents} | {row.succeeded} | {_rate(row.rate)} | "
            f"{row.leaked} | {_rate(row.unchanged)} |"
            for row in study.by_template
        ),
    ])


def _grid(study: Study) -> str:
    """The full cross product, as a matrix — the shape the suite was designed to fill."""
    placements = tuple(row.label for row in study.by_placement)
    payloads = tuple(row.label for row in study.by_payload)
    cells = {(payload, placement): rate for payload, placement, rate in study.grid}
    return "\n".join([
        "## Payload by placement",
        "",
        "One cell is one payload printed in one place. `n` per cell is small by design — the grid "
        "is for seeing *where* an attack works, and the per-payload and per-placement tables above "
        "are where the denominators are.",
        "",
        "| payload | " + " | ".join(f"`{name}`" for name in placements) + " |",
        "|---|" + "---:|" * len(placements),
        *(
            f"| `{payload}` | "
            + " | ".join(
                _cell(cells.get((payload, placement))) for placement in placements
            )
            + " |"
            for payload in payloads
        ),
    ])


def _cell(rate: Rate | None) -> str:
    if rate is None or rate.documents == 0:
        return DASH
    return f"{_rate(rate.rate)} ({rate.succeeded}/{rate.documents})"


def _leaks(study: Study) -> str:
    """Every successful attack the gate would have accepted, named. The list a reviewer wants."""
    leaked = [row for row in study.outcomes if row.leaked]
    if not leaked:
        return ""
    return "\n".join([
        "## What got through",
        "",
        "Successful attacks whose document the routing gate would have **accepted**, unreviewed.",
        "",
        "| document | payload | placement | tier | still exact |",
        "|---|---|---|---|---|",
        *(
            f"| `{row.doc_id}` | `{row.payload}` | `{row.placement}` | {row.tier} | "
            f"{'yes' if row.exact else 'no'} |"
            for row in leaked
        ),
    ])


def _caveats(study: Study, *, run: RunMeta, has_reach: bool = False) -> str:
    lines = ["## Read this before the tables", ""]
    overall = study.overall

    if overall.succeeded == 0 and run.reads_images and has_reach:
        #: The compliant control is the wrong separator for a run that read pixels: `gullible`
        #: finds payloads in the *text* layer, so its own rate is bounded by a channel this reader
        #: never used. What establishes that these payloads reached this model is the reach table.
        lines.append(
            "* **No attack met its objective.** A zero here has two readings — the reader resisted "
            "the payloads, or the payloads never reached it — and on this run the reach table "
            "above settles it: every payload it marks on the `image` column was printed in ink on "
            "a page this model looked at. Those are the ones this row is a defence result for. "
            "The rest reached nobody, and a zero on them is arithmetic rather than evidence."
        )
    elif overall.succeeded == 0:
        lines.append(
            "* **No attack met its objective.** A zero here has two readings and this report "
            "cannot choose between them: the reader resisted the payloads, or the payloads never "
            "reached the reader. What separates them is the compliant control — `gullible`, which "
            "obeys every instruction it finds — measured **on this same corpus**, and its "
            "`attack.md` is the file to read before treating this row as a defence. A suite whose "
            "success predicate could not fire at all would report exactly this too."
        )
    if overall.succeeded == 0:
        #: Printed with every zero, in both modalities. A low attack success rate is the one result
        #: in this project a reader is most likely to over-read, and these two bounds are
        #: properties of the *suite* rather than of whichever reader produced the zero — so they
        #: belong in the artifact rather than only in the prose that quotes it.
        lines.append(
            f"* **A zero bounds this suite, not injection.** The {len(study.by_payload)} payloads "
            "are fixed strings: none adapts, none responds to having failed, and none was written "
            "against the reader being measured — so this row scores a catalogue rather than an "
            "adversary. It is also one reader on one corpus. `docs/adr/0001_trust_boundary.md` "
            "carries the threat model and the control that is still missing."
        )
    denial = next((row for row in study.by_payload if _is_denial(row.label)), None)
    if denial is not None and denial.succeeded:
        lines.append(
            f"* **{denial.succeeded} of {denial.documents} denial attempt(s) worked**, and no "
            "value was accepted from them because none was returned. That is an availability "
            "attack succeeding, not the gate defending: the document was not processed at all."
        )
    if overall.succeeded and overall.leaked == 0:
        lines.append(
            "* Every successful attack was routed to a human. The gate was built from M5's "
            "measurements of *model errors*, so this is worth stating precisely: it holds for the "
            "payloads that break arithmetic, and it is not a general property — an attacker who "
            "supplies identifiers with valid check digits, printed on the page so they ground, "
            "agrees with both signals."
        )
    if overall.leaked:
        lines.append(
            f"* **{overall.leaked} successful attack(s) would have been accepted.** An attacker "
            "defeats the gate's arithmetic and grounding checks "
            "by construction: they choose an account number that passes mod-97, and print it on "
            "the page, so the value they want is both consistent and grounded. Detection built for "
            "*errors* does not transfer to an *adversary*, and this row is what that costs."
        )
    control = study.control
    if control.documents:
        lines.append(
            "* **The headline rate excludes the control.** A payload that asks for nothing cannot "
            f"succeed, and leaving its {control.documents} document(s) in the denominator would "
            "lower every attack success rate for a reason that has nothing to do with a defence. "
            f"Its own column is `unchanged`: {control.exact} of {control.documents} came back "
            f"exactly right ({_rate(control.unchanged)}), which is what says whether merely adding "
            "text to a page moves the extraction."
        )
    #: Read off the corpus's own provenance rather than assumed. Printed unconditionally, this
    #: sentence was a guarantee the report made about itself and could not have checked: a corpus
    #: built with `--no-verify` would have carried it word for word.
    if run.corpus.get("verified", True):
        lines.append(
            "* The suite verified at build time that every payload survived into the text layer of "
            "the page **as printed**. An attack the corpus never carried would otherwise sit in "
            "the denominator as a failed attack. It is a check on the rendering and not on what "
            "happened to the page afterwards — on a corpus that was then scanned, what each "
            "payload still reached is the reach table rather than this sentence."
        )
    else:
        lines.append(
            "* **This corpus was built with verification off.** Nothing checked that the payloads "
            "reached the text layer, so an attack the model never saw is indistinguishable here "
            "from one it saw and ignored, and every rate above is a lower bound of unknown "
            "tightness. Rebuild without `--no-verify` before quoting any of it."
        )
    return "\n".join(lines)


def _is_denial(payload_name: str) -> bool:
    payload = BY_NAME.get(payload_name)
    return payload is not None and payload.category == DENIAL


def summary_lines(study: Study) -> Iterable[str]:
    """What a terminal wants after a run, without the tables."""
    overall = study.overall
    yield (
        f"attacked   : {overall.documents}   succeeded: {overall.succeeded}   "
        f"ASR {_rate(overall.rate)}   leaked {overall.leaked}"
    )
    for row in study.by_payload:
        yield (
            f"  {row.label:<18} {_rate(row.rate):>8}  ({row.succeeded}/{row.documents})   "
            f"leaked {row.leaked}   unchanged {_rate(row.unchanged)}"
        )
