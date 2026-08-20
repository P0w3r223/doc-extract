"""Build the scanned corpus — the same invoices, printed and then photographed.

    python -m doc_extract.degrade --out data/scanned
    python -m doc_extract.degrade --attacked --out data/attacked-scanned

The seed and the tier set default to M2's, and that is not a convenience: like the foreign corpus,
this one is only a paired comparison while both halves are built from the same integer. Changing it
here without changing it there produces two corpora that share document names and nothing else.

`--attacked` scans M6's grid instead of M2's corpus — every payload, in every placement, at every
rung — and writes `attacks.jsonl` and `reach.jsonl` beside the manifest. See `degrade/attacked.py`
for what the second of those measures and why it is not the first.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from doc_extract.attack.payloads import BY_NAME as PAYLOADS_BY_NAME
from doc_extract.attack.payloads import PAYLOADS
from doc_extract.attack.suite import ATTACKS_NAME, Assignment, SuiteError
from doc_extract.degrade import attacked as attacked_corpus
from doc_extract.degrade import corpus
from doc_extract.degrade.attacked import Reach
from doc_extract.degrade.rungs import BY_NAME as RUNGS_BY_NAME
from doc_extract.degrade.rungs import RUNGS
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.overlay import PLACEMENTS
from doc_extract.synth.tiers import BY_NAME, TIERS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="doc_extract.degrade", description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/scanned"),
                        help="directory to write the corpus into (default: data/scanned)")
    parser.add_argument("--seed", type=int, default=synth_corpus.DEFAULT_SEED,
                        help=f"corpus seed; must match the synthetic corpus's to stay a paired "
                             f"comparison (default: {synth_corpus.DEFAULT_SEED})")
    parser.add_argument("--per-tier", type=int, default=synth_corpus.DEFAULT_PER_TIER,
                        help=f"documents per tier (default: {synth_corpus.DEFAULT_PER_TIER})")
    parser.add_argument("--tier", action="append", choices=sorted(BY_NAME),
                        help="restrict to one tier; may be repeated")
    parser.add_argument("--rung", action="append", choices=sorted(RUNGS_BY_NAME),
                        help="restrict to one rung of legibility; may be repeated")
    parser.add_argument("--attacked", action="store_true",
                        help="scan M6's attacked grid rather than the clean corpus")
    parser.add_argument("--per-cell", type=int, default=attacked_corpus.DEFAULT_PER_CELL,
                        help="with --attacked: documents per payload x placement cell, before the "
                             f"rungs multiply them (default: {attacked_corpus.DEFAULT_PER_CELL})")
    parser.add_argument("--payload", action="append", default=[],
                        choices=sorted(PAYLOADS_BY_NAME),
                        help="with --attacked: restrict to one payload; may be repeated")
    parser.add_argument("--placement", action="append", default=[], choices=sorted(PLACEMENTS),
                        help="with --attacked: restrict to one placement; may be repeated")
    parser.add_argument("--no-verify", action="store_true",
                        help="with --attacked: skip checking each payload reached the printed page")
    parser.add_argument("--quiet", action="store_true", help="no per-document line")
    args = parser.parse_args(argv)

    rungs = tuple(RUNGS_BY_NAME[name] for name in args.rung) if args.rung else RUNGS
    if args.attacked:
        return _attacked(args, rungs)
    return _clean(args, rungs)


def _clean(args: argparse.Namespace, rungs: tuple) -> int:
    tiers = tuple(BY_NAME[name] for name in args.tier) if args.tier else TIERS
    entries = corpus.generate(
        args.out, seed=args.seed, per_tier=args.per_tier, tiers=tiers, rungs=rungs
    )

    by_rung = Counter(entry.template for entry in entries)
    with_text = ", ".join(rung.name for rung in rungs if rung.text_layer) or "none"
    print(f"{len(entries)} documents -> {args.out}")
    print(f"  rungs     : {', '.join(f'{k} {v}' for k, v in sorted(by_rung.items()))}")
    print(f"  text layer: {with_text}")
    print(f"  pages     : {sum(entry.pages for entry in entries)}")
    print(f"  manifest  : {args.out / synth_corpus.MANIFEST_NAME}")
    return 0


def _attacked(args: argparse.Namespace, rungs: tuple) -> int:
    """M6's grid, scanned. The tier filter does not apply: the suite picks its own base documents.

    Rejected rather than ignored, because a `--tier` that silently did nothing would produce a
    corpus the caller believes is restricted and the manifest says is not.
    """
    if args.tier:
        print("error: --tier does not apply with --attacked; the suite chooses its base documents "
              "by placement and slot, and restricting the pool would change which invoices the "
              "grid is paired over. Use --payload or --placement")
        return 2

    payloads = (
        tuple(PAYLOADS_BY_NAME[name] for name in args.payload) if args.payload else PAYLOADS
    )
    placements = tuple(args.placement) if args.placement else PLACEMENTS
    try:
        entries, _, reaches = attacked_corpus.generate(
            args.out,
            per_cell=args.per_cell,
            payloads=payloads,
            placements=placements,
            rungs=rungs,
            seed=args.seed,
            per_tier=args.per_tier,
            verify=not args.no_verify,
            progress=None if args.quiet else _progress,
        )
    except SuiteError as error:
        print(f"error: {error}")
        return 2

    by_rung = Counter(entry.template for entry in entries)
    print(f"{len(entries)} attacked documents -> {args.out}")
    print(f"  rungs      : {', '.join(f'{k} {v}' for k, v in sorted(by_rung.items()))}")
    print(f"  payloads   : {', '.join(payload.name for payload in payloads)}")
    print(f"  placements : {', '.join(placements)}")
    print(f"  reached a text layer : {sum(1 for row in reaches if row.in_text_layer)}")
    print(f"  reached the image    : {sum(1 for row in reaches if row.on_the_image)}")
    print(f"  reached nobody       : {sum(1 for row in reaches if row.reaches_nobody)}")
    print(f"  verified   : {'no — payloads unchecked' if args.no_verify else 'every payload'}")
    print(f"  manifest   : {args.out / synth_corpus.MANIFEST_NAME}")
    print(f"  attacks    : {args.out / ATTACKS_NAME}")
    print(f"  reach      : {args.out / attacked_corpus.REACH_NAME}")
    return 0


def _progress(assignment: Assignment, reach: Reach) -> None:
    channels = ",".join(
        name for name, reached in
        (("text", reach.in_text_layer), ("image", reach.on_the_image)) if reached
    ) or "nobody"
    print(f"  {assignment.doc_id:<48} {assignment.tier:<12} -> {channels}")


if __name__ == "__main__":
    raise SystemExit(main())
