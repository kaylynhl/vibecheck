"""Download the Kaggle Spotify 1M-tracks catalog into ``spotify/``.

The Kaggle CSV (~168 MB) backs the local playlist catalog. It is gitignored
because of its size, so each contributor / grader needs to fetch it once
locally. This script is the reproducible path -- it requires a free Kaggle
API token at ``~/.kaggle/kaggle.json`` (Settings -> API -> Create New Token
on kaggle.com).

Usage::

    python scripts/download_spotify_catalog.py
    python scripts/download_spotify_catalog.py --force   # re-download even if present

The script copies the CSV out of kagglehub's cache into
``spotify/spotify_data.csv`` so the rest of the codebase can find it at the
expected path.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_PATH = ROOT / "spotify" / "spotify_data.csv"
DATASET_ID = "amitanshjoshi/spotify-1million-tracks"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if spotify/spotify_data.csv already exists.",
    )
    parser.add_argument(
        "--dataset",
        default=DATASET_ID,
        help=f"Kaggle dataset slug (default: {DATASET_ID}).",
    )
    args = parser.parse_args()

    if TARGET_PATH.exists() and not args.force:
        size_mb = TARGET_PATH.stat().st_size / (1024 * 1024)
        print(
            f"Already present at {TARGET_PATH} ({size_mb:.1f} MB). "
            "Use --force to re-download."
        )
        return 0

    try:
        import kagglehub  # type: ignore[import-untyped]
    except ImportError:
        print(
            "kagglehub is not installed. Install it with:\n"
            "    pip install kagglehub\n"
            "Then create a Kaggle API token: "
            "https://www.kaggle.com/settings -> API -> Create New Token "
            "and save it to ~/.kaggle/kaggle.json (chmod 600).",
            file=sys.stderr,
        )
        return 2

    print(f">> Downloading {args.dataset} ...")
    cached_dir = Path(kagglehub.dataset_download(args.dataset))
    csvs = sorted(cached_dir.glob("*.csv"))
    if not csvs:
        print(
            f"No CSV found in download cache {cached_dir}. "
            "The dataset layout may have changed.",
            file=sys.stderr,
        )
        return 1
    source = csvs[0]
    TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(source, TARGET_PATH)
    size_mb = TARGET_PATH.stat().st_size / (1024 * 1024)
    print(f">> Wrote {TARGET_PATH} ({size_mb:.1f} MB).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
