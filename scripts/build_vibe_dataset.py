"""Mine ``filtered_reddit_texts.csv`` for posts that mention a known aesthetic,
extract structured tags from each, and write a labeled ``(tag_vector, vibe)``
training set used by ``scripts/train_vibe_classifier.py``.

Run::

    python scripts/build_vibe_dataset.py            # default paths
    python scripts/build_vibe_dataset.py --rebuild  # ignore existing output

The output is a single CSV at ``data/processed/vibe_train.csv`` with columns::

    vibe, tag_count, feature_vector_b64, source_excerpt

We store feature vectors as base64-encoded float32 NumPy arrays so the file
stays compact, and so it can be reloaded without re-running tag extraction.
"""

from __future__ import annotations

import argparse
import base64
import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np  # noqa: E402

from vibecheck.errors import TagExtractionError  # noqa: E402
from vibecheck.tags.extract import extract_structured_tags  # noqa: E402
from vibecheck.vibe.catalog import VIBE_PROFILES  # noqa: E402


DEFAULT_CORPUS = ROOT / "reddit" / "filtered_reddit_texts.csv"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "vibe_train.csv"
MIN_TAGS_PER_EXAMPLE = 1

# Aliases tied to each canonical vibe name. We need these because the Reddit
# corpus has a hard October-2018 cutoff: aesthetics that became popular after
# 2018 (cottagecore, dark academia, clean girl, coastal grandmother, light
# academia, japandi, soft girl) have very weak coverage in the raw text. The
# older labels below have decent representation under common synonyms
# ("boho", "scandi", "midcentury", etc.). Distant-supervision style: any
# alias counts as a label.
VIBE_ALIASES: dict[str, tuple[str, ...]] = {
    "cottagecore": ("cottagecore", "prairie style"),
    "dark academia": ("dark academia",),
    "minimalist": ("minimalist", "minimalism", "minimalistic"),
    "y2k": ("y2k", "2000s style", "early 2000s"),
    "coastal grandmother": ("coastal grandmother",),
    "indie sleaze": ("indie sleaze", "indie scene"),
    "clean girl": ("clean girl",),
    "cyberpunk": ("cyberpunk", "techwear"),
    "bohemian": ("bohemian", "boho"),
    "old money": ("old money",),
    "grunge": ("grunge", "grungy"),
    "soft girl": ("soft girl", "soft girly"),
    "goblincore": ("goblincore",),
    "light academia": ("light academia",),
    "streetwear": ("streetwear", "street style", "hypebeast"),
    "mid-century modern": ("mid-century modern", "mid-century", "midcentury", "mcm"),
    "scandinavian": ("scandinavian", "scandi", "nordic style"),
    "industrial": ("industrial style", "industrial decor", "industrial design"),
    "maximalist": ("maximalist", "maximalism"),
    "japandi": ("japandi",),
}


def vibe_match_patterns() -> list[tuple[str, re.Pattern[str]]]:
    """Return (vibe_name, compiled regex) pairs, longest aliases first.

    For each canonical vibe we try every alias; longest aliases are checked
    first so multi-word phrases like "dark academia" win over single-word
    substrings that may appear inside them.
    """
    entries: list[tuple[str, str]] = []
    for vibe, aliases in VIBE_ALIASES.items():
        for alias in aliases:
            entries.append((vibe, alias))
    entries.sort(key=lambda pair: -len(pair[1]))
    return [
        (vibe, re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)", re.IGNORECASE))
        for vibe, alias in entries
    ]


def find_first_vibe(text: str, patterns: list[tuple[str, re.Pattern[str]]]) -> str | None:
    """Return the longest vibe name whose pattern matches ``text``, else None."""
    for name, pattern in patterns:
        if pattern.search(text):
            return name
    return None


def build_feature_index() -> list[tuple[str, str]]:
    """Stable ordered list of (category, value) pairs used as the feature axis."""
    from vibecheck.tags.vocabulary import TAG_VOCABULARY

    pairs: list[tuple[str, str]] = []
    for category in sorted(TAG_VOCABULARY):
        for value in sorted(TAG_VOCABULARY[category]):
            pairs.append((category, value))
    return pairs


def tags_to_feature_vector(tags, feature_index: list[tuple[str, str]]) -> np.ndarray:
    """Pack a tag list into a fixed-length confidence vector aligned to feature_index."""
    vec = np.zeros(len(feature_index), dtype=np.float32)
    lookup = {pair: i for i, pair in enumerate(feature_index)}
    for tag in tags:
        idx = lookup.get((tag.category, tag.value))
        if idx is None:
            continue
        vec[idx] = max(vec[idx], float(tag.confidence))
    return vec


def encode_vector(vec: np.ndarray) -> str:
    """Encode a float32 vector as a base64 string for compact CSV storage."""
    return base64.b64encode(vec.astype(np.float32).tobytes()).decode("ascii")


def iter_corpus(path: Path):
    """Yield raw text rows from a single-column Reddit dump (no header)."""
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row:
                continue
            text = row[0].strip()
            if text:
                yield text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap rows scanned (useful for quick iteration).",
    )
    parser.add_argument("--rebuild", action="store_true", help="Overwrite existing output.")
    args = parser.parse_args()

    if not args.corpus.exists():
        print(f"Corpus not found: {args.corpus}", file=sys.stderr)
        return 2

    if args.output.exists() and not args.rebuild:
        print(f"Output already exists at {args.output} (use --rebuild to overwrite).")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)

    patterns = vibe_match_patterns()
    feature_index = build_feature_index()

    scanned = 0
    kept = 0
    per_vibe = Counter()

    with args.output.open("w", encoding="utf-8", newline="") as out_fh:
        writer = csv.writer(out_fh)
        writer.writerow(["vibe", "tag_count", "feature_vector_b64", "source_excerpt"])
        for text in iter_corpus(args.corpus):
            scanned += 1
            if args.limit and scanned > args.limit:
                break

            vibe = find_first_vibe(text, patterns)
            if vibe is None:
                continue

            try:
                tags = extract_structured_tags(text)
            except TagExtractionError:
                continue

            if len(tags) < MIN_TAGS_PER_EXAMPLE:
                continue

            vec = tags_to_feature_vector(tags, feature_index)
            if not np.any(vec):
                continue

            excerpt = " ".join(text.split())[:200]
            writer.writerow([vibe, len(tags), encode_vector(vec), excerpt])
            kept += 1
            per_vibe[vibe] += 1

    print(f"Scanned {scanned:,} rows, kept {kept:,} labeled examples.")
    print(f"Wrote: {args.output}")
    print()
    print("Per-vibe counts:")
    for vibe, count in sorted(per_vibe.items(), key=lambda kv: -kv[1]):
        print(f"  {vibe:24s} {count}")
    if not per_vibe:
        print("  (none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
