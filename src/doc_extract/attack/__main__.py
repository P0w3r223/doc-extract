"""Build the attacked corpus: the same invoices, with one injected string each.

    python -m doc_extract.attack --out data/attacked
    python -m doc_extract.attack --out data/attacked --per-cell 2 --payload total_override

The output is a corpus in the shape `eval.dataset` already reads — manifest, provenance, one XML and
one PDF per document — plus `attacks.jsonl`, which says which payload was printed on which document
and where. The gold is the base document's gold, unchanged: an injected instruction does not alter
what the invoice says, so every M4 and M5 measurement runs over this corpus unmodified.

Nothing here calls a model. Building the corpus is rendering and parsing; measuring what a model
does with it is `python -m doc_extract.eval run --corpus data/attacked`.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from doc_extract.attack import suite
from doc_extract.attack.payloads import BY_NAME, PAYLOADS
from doc_extract.attack.suite import Assignment, SuiteError
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.overlay import PLACEMENTS

DEFAULT_OUT = Path("data/attacked")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="doc_extract.attack", description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="directory for the attacked corpus "
                             f"(default: {DEFAULT_OUT})")
    parser.add_argument("--per-cell", type=int, default=suite.DEFAULT_PER_CELL,
                        help="documents per payload x placement cell "
                             f"(default: {suite.DEFAULT_PER_CELL})")
    parser.add_argument("--payload", action="append", default=[], choices=sorted(BY_NAME),
                        help="restrict to one payload; may be repeated")
    parser.add_argument("--placement", action="append", default=[], choices=sorted(PLACEMENTS),
                        help="restrict to one placement; may be repeated")
    parser.add_argument("--seed", type=int, default=synth_corpus.DEFAULT_SEED,
                        help=f"seed of the base corpus (default: {synth_corpus.DEFAULT_SEED})")
    parser.add_argument("--per-tier", type=int, default=synth_corpus.DEFAULT_PER_TIER,
                        help="documents per tier in the base corpus "
                             f"(default: {synth_corpus.DEFAULT_PER_TIER})")
    parser.add_argument("--no-verify", action="store_true",
                        help="skip reading each page back to check the payload survived rendering")
    parser.add_argument("--quiet", action="store_true", help="no per-document line")
    args = parser.parse_args(argv)

    payloads = (
        tuple(BY_NAME[name] for name in args.payload) if args.payload else PAYLOADS
    )
    placements = tuple(args.placement) if args.placement else PLACEMENTS

    try:
        entries, assignments = suite.generate(
            args.out,
            per_cell=args.per_cell,
            payloads=payloads,
            placements=placements,
            seed=args.seed,
            per_tier=args.per_tier,
            verify=not args.no_verify,
            progress=None if args.quiet else _progress,
        )
    except SuiteError as error:
        print(f"error: {error}")
        return 2

    by_placement = Counter(assignment.placement for assignment in assignments)
    print(f"{len(entries)} attacked documents -> {args.out}")
    print(f"  payloads   : {', '.join(payload.name for payload in payloads)}")
    print(f"  placements : {', '.join(f'{k} {v}' for k, v in sorted(by_placement.items()))}")
    print(f"  tiers      : {len({assignment.tier for assignment in assignments})} represented")
    print(f"  verified   : {'no — payloads unchecked' if args.no_verify else 'every payload'}")
    print(f"  manifest   : {args.out / synth_corpus.MANIFEST_NAME}")
    print(f"  attacks    : {args.out / suite.ATTACKS_NAME}")
    return 0


def _progress(assignment: Assignment) -> None:
    print(f"  {assignment.doc_id:<34} {assignment.tier}/{assignment.template}")


if __name__ == "__main__":
    raise SystemExit(main())
