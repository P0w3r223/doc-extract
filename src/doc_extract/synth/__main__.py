"""Build the synthetic corpus.

    python -m doc_extract.synth --out data/synthetic --per-tier 12 --seed 20260818

The defaults reproduce the corpus the reported numbers were computed on; anything else is an
experiment and should say so in the run that used it.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from doc_extract.synth import corpus
from doc_extract.synth.tiers import BY_NAME, TIERS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="doc_extract.synth", description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/synthetic"),
                        help="directory to write the corpus into (default: data/synthetic)")
    parser.add_argument("--seed", type=int, default=corpus.DEFAULT_SEED,
                        help=f"corpus seed (default: {corpus.DEFAULT_SEED})")
    parser.add_argument("--per-tier", type=int, default=corpus.DEFAULT_PER_TIER,
                        help=f"documents per difficulty tier (default: {corpus.DEFAULT_PER_TIER})")
    parser.add_argument("--tier", action="append", choices=sorted(BY_NAME),
                        help="restrict to one tier; may be repeated")
    args = parser.parse_args(argv)

    tiers = tuple(BY_NAME[name] for name in args.tier) if args.tier else TIERS
    entries = corpus.generate(args.out, seed=args.seed, per_tier=args.per_tier, tiers=tiers)

    by_template = Counter(entry.template for entry in entries)
    pages = sum(entry.pages for entry in entries)
    print(f"{len(entries)} documents -> {args.out}")
    print(f"  tiers     : {', '.join(tier.name for tier in tiers)}")
    print(f"  templates : {', '.join(f'{k} {v}' for k, v in sorted(by_template.items()))}")
    print(f"  pages     : {pages}")
    print(f"  manifest  : {args.out / 'manifest.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
