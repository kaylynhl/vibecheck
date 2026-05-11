"""Precompute and cache the playlist title index.

By default reads the bundled seed set at ``data/seed/playlist_seeds.json``
so the pipeline works without any external download. Pass ``--source
<path-to-csv>`` to use the Kaggle Spotify Playlists dataset instead
(https://www.kaggle.com/datasets/andrewmvd/spotify-playlists).

Run::

    python scripts/build_playlist_index.py            # seed set
    python scripts/build_playlist_index.py --source data/raw/spotify_playlists.csv
    python scripts/build_playlist_index.py --rebuild  # ignore cached .npy
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibecheck.rec.playlists import DEFAULT_CACHE_PATH, load_playlist_index  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Path to a Spotify-style playlist CSV. Falls back to the seed set if omitted.",
    )
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_PATH)
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    index = load_playlist_index(
        source_csv=args.source,
        cache_path=args.cache,
        rebuild=args.rebuild,
    )
    print(
        f"Built playlist index with {len(index.playlists)} titles "
        f"(dim={index.embeddings.shape[1]})."
    )
    print(f"Cached embeddings: {args.cache}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
