"""Selection ablation: compare plain NN vs. selector variants on a single query.

Run::

    python scripts/ablate_selection.py --query "cottagecore floral linen prairie"

Prints four side-by-side rankings of product titles so you can eyeball how the
diversity and complementarity terms change the result. Designed for the report's
ablation table.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibecheck.rec import (  # noqa: E402
    RecommendationConfig,
    SelectionConfig,
    recommend_items,
)
from vibecheck.schemas import ExtractedTag, VisionAnalysisPayload  # noqa: E402


def make_payload(query: str) -> VisionAnalysisPayload:
    """Build a minimal payload from a free-text query so we can skip Groq."""
    return VisionAnalysisPayload(
        scene_type="outfit",
        visual_summary=query,
        palette=[],
        lighting=[],
        textures=[],
        patterns=[],
        silhouette_or_shape=[],
        objects_or_items=[],
        mood_descriptors=[],
        aesthetic_descriptors=[],
        vibe_query=query,
        uncertainty_notes=[],
        observed_facts=[],
        uncertain_inferences=[],
    )


def parse_image_tags(raw: str) -> list[ExtractedTag]:
    """Parse "category:value,category:value" pairs into ExtractedTag objects."""
    tags: list[ExtractedTag] = []
    if not raw:
        return tags
    for part in raw.split(","):
        if ":" not in part:
            continue
        category, value = part.split(":", 1)
        tags.append(
            ExtractedTag(
                category=category.strip(),
                value=value.strip(),
                confidence=1.0,
                evidence=value.strip(),
            )
        )
    return tags


CONFIGS: list[tuple[str, RecommendationConfig]] = [
    ("plain NN", RecommendationConfig()),
    (
        "+ complementarity",
        RecommendationConfig(
            selection=SelectionConfig(use_diversity=False, use_complementarity=True)
        ),
    ),
    (
        "+ diversity",
        RecommendationConfig(
            selection=SelectionConfig(use_diversity=True, use_complementarity=False)
        ),
    ),
    (
        "+ both (full)",
        RecommendationConfig(
            selection=SelectionConfig(use_diversity=True, use_complementarity=True)
        ),
    ),
]


def truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text.ljust(width)
    return text[: width - 1] + "\u2026"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True, help="Free-text vibe query.")
    parser.add_argument(
        "--image-tags",
        default="",
        help=(
            "Optional comma-separated category:value pairs simulating image tags "
            "(e.g. 'palette:warm neutrals,texture:linen'). Only used by the "
            "complementarity term."
        ),
    )
    parser.add_argument(
        "--top-k", type=int, default=5, help="Items per ranking column (default: 5)."
    )
    args = parser.parse_args()

    payload = make_payload(args.query)
    image_tags = parse_image_tags(args.image_tags)

    rankings: list[tuple[str, list[dict[str, object]]]] = []
    for label, config in CONFIGS:
        cfg = RecommendationConfig(
            top_k=args.top_k,
            k_corpus=config.k_corpus,
            alpha=config.alpha,
            beta=config.beta,
            selection=config.selection,
            candidate_pool_size=config.candidate_pool_size,
        )
        items = recommend_items(payload, config=cfg, image_tags=image_tags)
        rankings.append((label, items))

    col = 38
    header = " | ".join(truncate(label, col) for label, _ in rankings)
    print(header)
    print("-" * len(header))
    for rank in range(args.top_k):
        row_cells: list[str] = []
        for _, items in rankings:
            if rank >= len(items):
                row_cells.append(truncate("", col))
                continue
            item = items[rank]
            title = str(item.get("name") or item.get("title") or item.get("id") or "?")
            score = float(item.get("score", 0.0))
            cell = f"{rank + 1}. {title}  ({score:.3f})"
            row_cells.append(truncate(cell, col))
        print(" | ".join(row_cells))

    print()
    print("Image tag categories used for complementarity:",
          sorted({t.category for t in image_tags}) or "(none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
