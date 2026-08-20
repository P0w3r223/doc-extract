"""Build the scanned corpus — the same invoices, printed and then photographed.

    python -m doc_extract.degrade --out data/scanned

The seed and the tier set default to M2's, and that is not a convenience: like the foreign corpus,
this one is only a paired comparison while both halves are built from the same integer. Changing it
here without changing it there produces two corpora that share document names and nothing else.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from doc_extract.degrade import corpus
from doc_extract.degrade.rungs import BY_NAME as RUNGS_BY_NAME
from doc_extract.degrade.rungs import RUNGS
from doc_extract.synth import corpus as synth_corpus
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
    args = parser.parse_args(argv)

    tiers = tuple(BY_NAME[name] for name in args.tier) if args.tier else TIERS
    rungs = tuple(RUNGS_BY_NAME[name] for name in args.rung) if args.rung else RUNGS
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


if __name__ == "__main__":
    raise SystemExit(main())
