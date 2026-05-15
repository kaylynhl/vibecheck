"""Precompute and cache the Spotify audio index normalisation stats.

Run this once after adding ``spotify/spotify_data.csv`` so that subsequent
calls to ``load_audio_index()`` load instantly from the cached JSON instead
of recomputing min/max stats from the full CSV.

Usage::

    python scripts/build_playlist_index.py            # build, skip if cached
    python scripts/build_playlist_index.py --rebuild  # recompute even if cached
    python scripts/build_playlist_index.py --smoke-test  # score one vibe and print results
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

from vibecheck.rec.spotify_audio import (  # noqa: E402
    AESTHETIC_AUDIO_PROFILES,
    DEFAULT_CACHE,
    DEFAULT_CSV,
    load_audio_index,
    score_tracks,
)


def smoke_test(aesthetic: str = "dark_academia", top_k: int = 5) -> None:
    print(f"\n── Smoke test: '{aesthetic}' (top {top_k}) ──")
    index = load_audio_index()
    tracks = score_tracks(aesthetic, index, top_k=top_k)
    print(f"{'score':>6}  {'artist':<22} {'track':<35} genre")
    print("-" * 80)
    for t in tracks:
        print(
            f"{t['vibe_score']:>6.3f}  "
            f"{t['artist_name']:<22.22}  "
            f"{t['track_name']:<35.35}  "
            f"{t['genre']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Recompute normalisation stats even if cache already exists.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Path to spotify_data.csv (default: {DEFAULT_CSV}).",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=DEFAULT_CACHE,
        help=f"Where to write the JSON stats cache (default: {DEFAULT_CACHE}).",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="After building, score 'dark_academia' and print the top-5 results.",
    )
    parser.add_argument(
        "--smoke-aesthetic",
        default="dark_academia",
        help="Which aesthetic to use for the smoke test (default: dark_academia).",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        print(
            f"CSV not found: {args.csv}\n"
            "The Spotify dataset is gitignored due to its size.\n"
            "Place spotify_data.csv inside the spotify/ directory and rerun.",
            file=sys.stderr,
        )
        return 2

    if args.cache.exists() and not args.rebuild:
        print(f"Cache already exists at {args.cache} (use --rebuild to overwrite).")
    else:
        print(f">> Loading {args.csv.name} ...")
        start = perf_counter()
        index = load_audio_index(
            csv_path=args.csv,
            cache_path=args.cache,
            rebuild=True,
        )
        elapsed = perf_counter() - start
        print(
            f"   {len(index.df):,} tracks  |  "
            f"{len(index.feature_cols)} feature cols  |  "
            f"{elapsed:.1f}s"
        )
        print(f"   Normalised features: {index.norm_stats}")
        print(f">> Stats cache written to {args.cache}")

    # Summary of profile coverage
    present_features: set[str] = set()
    if args.cache.exists():
        import json
        present_features = set(json.loads(args.cache.read_text()).keys())

    raw_features_in_profiles = {
        f for prof in AESTHETIC_AUDIO_PROFILES.values() for f in prof
        if f in {"loudness", "tempo"}
    }
    missing = raw_features_in_profiles - present_features
    if missing:
        print(
            f"\nWarning: raw features {missing} appear in profiles but were not "
            "found in the CSV. Scoring will fall back to unnormalised values.",
            file=sys.stderr,
        )

    print(f"\nAudio profiles loaded: {len(AESTHETIC_AUDIO_PROFILES)} aesthetics")

    if args.smoke_test:
        smoke_test(args.smoke_aesthetic)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())