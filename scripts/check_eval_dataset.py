"""Check whether the CLIP-LoRA labeled photo dataset is ready to run.

The handoff's remaining ML work depends on real photos in
``data/eval/<aesthetic>/``. This script gives the team a quick, honest gate:
it verifies that every expected class folder exists and has enough images for
the stratified 60/20/20 split used by ``notebooks/demo.ipynb``.

Usage:
    python scripts/check_eval_dataset.py
    python scripts/check_eval_dataset.py --min-per-class 12
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = ROOT / "data" / "eval"

EXPECTED_CLASSES = (
    "minimalist",
    "dark_academia",
    "cottagecore",
    "grunge",
    "coastal_grandmother",
    "scandinavian",
    "mid_century_modern",
    "japandi",
)
IMG_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}


def count_images(data_root: Path) -> dict[str, int]:
    """Return image counts per expected class, treating missing dirs as zero."""
    counts: dict[str, int] = {}
    for cls in EXPECTED_CLASSES:
        cls_dir = data_root / cls
        if not cls_dir.is_dir():
            counts[cls] = 0
            continue
        counts[cls] = sum(
            1
            for path in cls_dir.iterdir()
            if path.is_file() and path.suffix.lower() in IMG_EXTS
        )
    return counts


def missing_classes(data_root: Path) -> list[str]:
    return [cls for cls in EXPECTED_CLASSES if not (data_root / cls).is_dir()]


def is_ready(counts: dict[str, int], min_per_class: int) -> bool:
    return all(counts.get(cls, 0) >= min_per_class for cls in EXPECTED_CLASSES)


def print_report(data_root: Path, counts: dict[str, int], min_per_class: int) -> None:
    print(f"Dataset root: {data_root}")
    print(f"Minimum per class: {min_per_class}")
    print()
    print(f"{'class':<24} {'images':>6}  status")
    print("-" * 42)
    for cls in EXPECTED_CLASSES:
        n = counts.get(cls, 0)
        status = "ready" if n >= min_per_class else f"needs {min_per_class - n}"
        print(f"{cls:<24} {n:>6}  {status}")
    print("-" * 42)
    total = sum(counts.values())
    print(f"{'total':<24} {total:>6}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--min-per-class", type=int, default=8)
    args = parser.parse_args()

    if args.min_per_class < 1:
        print("--min-per-class must be at least 1", file=sys.stderr)
        return 2
    if not args.data_root.exists():
        print(f"Dataset root not found: {args.data_root}", file=sys.stderr)
        return 2

    missing = missing_classes(args.data_root)
    counts = count_images(args.data_root)
    print_report(args.data_root, counts, args.min_per_class)
    sys.stdout.flush()

    if missing:
        print()
        print(f"Missing class folders: {', '.join(missing)}", file=sys.stderr)
        return 1
    if not is_ready(counts, args.min_per_class):
        print()
        print(
            "Dataset is not ready yet. Add personal photos to each "
            "data/eval/<aesthetic>/ folder, then rerun this check.",
            file=sys.stderr,
        )
        return 1

    print()
    print("Dataset is ready for Groq baseline export and CLIP-LoRA training.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
