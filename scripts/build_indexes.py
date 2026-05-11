"""Precompute and cache the Reddit + product FAISS indexes.

Run this once after a fresh checkout so that subsequent recommendation calls
load instantly from disk instead of re-encoding 62k Reddit posts.

Usage::

    python scripts/build_indexes.py            # build both, skip cached
    python scripts/build_indexes.py --rebuild  # rebuild even if cached
    python scripts/build_indexes.py --reddit-only
    python scripts/build_indexes.py --products-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    parser = argparse.ArgumentParser(description="Precompute vibecheck retrieval indexes.")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Recompute embeddings even if a cache file already exists.",
    )
    parser.add_argument(
        "--reddit-only",
        action="store_true",
        help="Only build the Reddit utterance index.",
    )
    parser.add_argument(
        "--products-only",
        action="store_true",
        help="Only build the product catalog index.",
    )
    args = parser.parse_args()

    if args.reddit_only and args.products_only:
        print("--reddit-only and --products-only are mutually exclusive.", file=sys.stderr)
        return 2

    from vibecheck.rec.encoder import FashionBertEncoder
    from vibecheck.rec.products import load_product_index
    from vibecheck.rec.text_index import load_reddit_index

    encoder = FashionBertEncoder()

    if not args.products_only:
        print(">> Building Reddit utterance index...")
        start = perf_counter()
        reddit_index = load_reddit_index(encoder=encoder, rebuild=args.rebuild)
        elapsed = perf_counter() - start
        print(f"   {len(reddit_index.texts):,} utterances, {reddit_index.embeddings.shape[1]} dims, {elapsed:.1f}s")

    if not args.reddit_only:
        print(">> Building product catalog index...")
        start = perf_counter()
        product_index = load_product_index(encoder=encoder, rebuild=args.rebuild)
        elapsed = perf_counter() - start
        print(f"   {len(product_index.products):,} products, {product_index.embeddings.shape[1]} dims, {elapsed:.1f}s")

    print(">> Done. Cached embeddings live in data/processed/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
