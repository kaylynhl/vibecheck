"""High-level recommendation entry point: vision payload -> ranked product list."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vibecheck.rec.encoder import FashionBertEncoder
from vibecheck.rec.expansion import expand_query
from vibecheck.rec.products import ProductIndex, load_product_index
from vibecheck.rec.select import SelectionConfig, select_items
from vibecheck.rec.text_index import RedditTextIndex, load_reddit_index
from vibecheck.schemas import ExtractedTag, VisionAnalysisPayload


@dataclass
class RecommendationConfig:
    """Knobs for the recommendation step.

    When ``selection`` is None the recommender returns the raw FAISS top-K.
    When set, it pulls ``candidate_pool_size`` items from FAISS and runs the
    greedy selector to pick ``top_k`` items optimizing vibe + complementarity
    - redundancy.
    """

    top_k: int = 10
    k_corpus: int = 10
    alpha: float = 1.0
    beta: float = 0.75
    selection: SelectionConfig | None = None
    candidate_pool_size: int = 50


def build_query_string(payload: VisionAnalysisPayload) -> str:
    """Turn a vision payload into a comma-separated vibe query string.

    Concatenates the most retrieval-relevant fields: ``vibe_query`` (already a
    keyword string), then the aesthetic and mood descriptors. Empty fields are
    skipped.
    """
    parts: list[str] = []
    if payload.vibe_query:
        parts.append(payload.vibe_query.strip())
    if payload.aesthetic_descriptors:
        parts.append(", ".join(payload.aesthetic_descriptors))
    if payload.mood_descriptors:
        parts.append(", ".join(payload.mood_descriptors))
    return ", ".join(p for p in parts if p)


# Module-level shared singletons: indexes are expensive to build; reuse them
# across calls within a single process.
_ENCODER: FashionBertEncoder | None = None
_REDDIT_INDEX: RedditTextIndex | None = None
_PRODUCT_INDEX: ProductIndex | None = None


def _shared_encoder() -> FashionBertEncoder:
    global _ENCODER
    if _ENCODER is None:
        _ENCODER = FashionBertEncoder()
    return _ENCODER


def _shared_reddit_index() -> RedditTextIndex:
    global _REDDIT_INDEX
    if _REDDIT_INDEX is None:
        _REDDIT_INDEX = load_reddit_index(encoder=_shared_encoder())
    return _REDDIT_INDEX


def _shared_product_index() -> ProductIndex:
    global _PRODUCT_INDEX
    if _PRODUCT_INDEX is None:
        _PRODUCT_INDEX = load_product_index(encoder=_shared_encoder())
    return _PRODUCT_INDEX


def recommend_items(
    payload: VisionAnalysisPayload,
    *,
    config: RecommendationConfig | None = None,
    image_tags: list[ExtractedTag] | None = None,
    encoder: FashionBertEncoder | None = None,
    reddit_index: RedditTextIndex | None = None,
    product_index: ProductIndex | None = None,
) -> list[dict[str, Any]]:
    """Run vibe-to-item recommendation: build query, expand, search products.

    Returns a list of JSON-safe product dicts (``Product.to_dict(score=...)``).
    When ``config.selection`` is set, the result dicts include a ``selection``
    sub-dict with the per-term score breakdown (vibe / complementarity /
    redundancy).

    ``image_tags`` is the list of structured tags already pulled from the
    user's photo(s); the selector uses their categories to compute the
    complementarity bonus. Tests and offline callers can inject their own
    ``encoder``, ``reddit_index``, and ``product_index`` to avoid touching
    disk or loading the model.
    """
    config = config or RecommendationConfig()
    encoder = encoder or _shared_encoder()
    reddit_index = reddit_index or _shared_reddit_index()
    product_index = product_index or _shared_product_index()

    query = build_query_string(payload)
    if not query:
        return []

    query_vec = encoder.encode([query])
    expanded = expand_query(
        query_vec,
        reddit_index,
        k_corpus=config.k_corpus,
        alpha=config.alpha,
        beta=config.beta,
    )

    if config.selection is None:
        results = product_index.search(expanded, k=config.top_k)
        return [product.to_dict(score=score) for score, _, product in results]

    pool_size = max(config.top_k, config.candidate_pool_size)
    pool = product_index.search(expanded, k=pool_size)
    if not pool:
        return []

    candidate_scores = [score for score, _, _ in pool]
    candidate_products = [product for _, _, product in pool]
    candidate_embeddings = product_index.embeddings[[idx for _, idx, _ in pool]]
    image_categories = {tag.category for tag in (image_tags or [])}

    selected = select_items(
        candidate_scores,
        candidate_embeddings,
        candidate_products,
        image_categories,
        top_k=config.top_k,
        config=config.selection,
    )
    return [
        {
            **result.product.to_dict(score=result.final_score),
            "selection": {
                "vibe_score": result.vibe_score,
                "complementarity": result.complementarity,
                "redundancy": result.redundancy,
            },
        }
        for result in selected
    ]


def reset_shared_state() -> None:
    """Drop module-level singletons. Only useful for tests."""
    global _ENCODER, _REDDIT_INDEX, _PRODUCT_INDEX
    _ENCODER = None
    _REDDIT_INDEX = None
    _PRODUCT_INDEX = None
