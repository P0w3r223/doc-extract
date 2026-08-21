"""Build the foreign corpus — the same invoices, printed by somebody else.

    python -m doc_extract.foreign --out data/foreign

The seed and the tier set default to M2's, and that is not a convenience: the corpus is only a
paired comparison while both halves are built from the same integer. Changing either here without
changing it there produces two corpora that share document names and nothing else, which is the one
way this measurement can be wrong without looking wrong.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from doc_extract.foreign import corpus
from doc_extract.foreign.dialect import TEMPLATES
from doc_extract.synth import corpus as synth_corpus
from doc_extract.synth.tiers import BY_NAME, TIERS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="doc_extract.foreign", description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/foreign"),
                        help="directory to write the corpus into (default: data/foreign)")
    parser.add_argument("--seed", type=int, default=synth_corpus.DEFAULT_SEED,
                        help=f"corpus seed; must match the synthetic corpus's to stay a paired "
                             f"comparison (default: {synth_corpus.DEFAULT_SEED})")
    parser.add_argument("--per-tier", type=int, default=synth_corpus.DEFAULT_PER_TIER,
                        help=f"documents per tier (default: {synth_corpus.DEFAULT_PER_TIER})")
    parser.add_argument("--tier", action="append", choices=sorted(BY_NAME),
                        help="restrict to one tier; may be repeated")
    args = parser.parse_args(argv)

    tiers = tuple(BY_NAME[name] for name in args.tier) if args.tier else TIERS
    entries = corpus.generate(args.out, seed=args.seed, per_tier=args.per_tier, tiers=tiers)

    by_template = Counter(entry.template for entry in entries)
    print(f"{len(entries)} documents -> {args.out}")
    print(f"  layouts   : {', '.join(f'{k} {v}' for k, v in sorted(by_template.items()))}")
    print(f"  vocabulary: {', '.join(TEMPLATES)} — none of them the synthetic corpus's")
    print(f"  pages     : {sum(entry.pages for entry in entries)}")
    print(f"  manifest  : {args.out / synth_corpus.MANIFEST_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
