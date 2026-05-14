"""Run the existing Groq Vision pipeline on every photo in `data/eval/` and
cache the top-1 predicted aesthetic per photo to a JSON file.

The cache file is the bridge between the production backend (which is the
canonical "Groq Vision" baseline for the report) and the offline training
notebook (`notebooks/demo.ipynb`). The notebook loads this JSON and reports
Groq's accuracy alongside CLIP zero-shot / linear probe / LoRA, so all four
systems are evaluated on the *exact same* held-out photos.

Usage:
    GROQ_API_KEY=... python scripts/export_groq_baseline.py

The script is idempotent and resumes: photos already in the cache are
skipped. Delete `data/eval/groq_predictions.json` to force a full re-run.

Output JSON shape (mapping absolute paths -> predicted class folder name):

    {
        "/Users/.../data/eval/minimalist/IMG_0001.jpg": "minimalist",
        "/Users/.../data/eval/grunge/IMG_0042.jpg": "dark_academia",
        ...
    }

Predictions that don't match one of our 8 trained classes are stored as
the model's raw label string -- the notebook treats anything outside the
class list as "abstain". This keeps the comparison honest: we don't
silently re-route Groq's "y2k" guess into "minimalist" just to get a hit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add the src layout to PYTHONPATH so we can run as `python scripts/...`
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vibecheck.pipeline import analyze_images  # noqa: E402

IMG_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}

DATA_ROOT = ROOT / "data" / "eval"
CACHE_PATH = DATA_ROOT / "groq_predictions.json"


def normalize_class_name(label: str) -> str:
    """Match the folder-name convention (snake_case)."""
    return label.strip().lower().replace(" ", "_").replace("-", "_")


def collect_photos() -> list[tuple[Path, str]]:
    """Walk `data/eval/<aesthetic>/*` and return (path, true_label) pairs."""
    pairs: list[tuple[Path, str]] = []
    for class_dir in sorted(DATA_ROOT.iterdir()):
        if not class_dir.is_dir() or class_dir.name.startswith("."):
            continue
        for img in sorted(class_dir.iterdir()):
            if img.suffix.lower() in IMG_EXTS:
                pairs.append((img, class_dir.name))
    return pairs


def load_cache() -> dict[str, str]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def save_cache(cache: dict[str, str]) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True))


def main() -> None:
    if not DATA_ROOT.exists():
        sys.exit(
            f"No labeled data found at {DATA_ROOT}. Drop photos into "
            "data/eval/<aesthetic>/ first."
        )

    photos = collect_photos()
    if not photos:
        sys.exit(
            f"No images found in {DATA_ROOT}/<aesthetic>/. "
            "Did you forget to copy your phone photos in?"
        )

    cache = load_cache()
    total = len(photos)
    new_calls = 0
    correct_in_cache = 0

    for i, (path, true_label) in enumerate(photos, start=1):
        key = str(path.resolve())
        if key in cache:
            # Already done in a previous run.
            if cache[key] == true_label:
                correct_in_cache += 1
            continue

        print(f"[{i:>3}/{total}] {path.relative_to(ROOT)} (true={true_label})", end=" ", flush=True)
        try:
            result = analyze_images([path], mode=None)
        except Exception as exc:  # network / API errors -- skip but keep going
            print(f"  ERROR: {exc}")
            continue

        if not result.top_vibes:
            pred = "abstain"
        else:
            pred = normalize_class_name(result.top_vibes[0].vibe)

        cache[key] = pred
        new_calls += 1
        marker = "OK" if pred == true_label else "X"
        print(f" -> {pred}  [{marker}]")

        # Persist after every call so a mid-run interrupt doesn't lose work.
        save_cache(cache)

    # Final summary
    correct = sum(1 for path, lbl in photos if cache.get(str(path.resolve())) == lbl)
    accuracy = correct / total if total else 0.0
    print()
    print(f"Groq baseline complete: {correct}/{total} = {accuracy:.1%} top-1 accuracy")
    print(f"New API calls this run: {new_calls}")
    print(f"Cache written to: {CACHE_PATH}")


if __name__ == "__main__":
    main()
