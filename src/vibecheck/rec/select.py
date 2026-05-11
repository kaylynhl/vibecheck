"""Greedy diversity- and complementarity-aware selection over candidate items.

This is the "search/optimization" step the proposal explicitly committed to.
Instead of returning the raw top-N from FAISS, we pull a larger candidate pool
and pick N items that maximize::

    w_vibe * vibe_similarity
        + w_complementarity * fraction_of_missing_tag_categories_filled
        - w_redundancy     * max_cosine_similarity_to_already_picked_items

All three terms are normalized to ``[0, 1]`` so the weights are interpretable.
The two ``use_*`` flags exist so we can run ablations against the report.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from vibecheck.errors import TagExtractionError
from vibecheck.rec.products import Product
from vibecheck.tags.extract import extract_structured_tags
from vibecheck.tags.vocabulary import TAG_CATEGORIES


@dataclass
class SelectionConfig:
    """Knobs for greedy item selection."""

    weight_vibe: float = 1.0
    weight_complementarity: float = 0.4
    weight_redundancy: float = 0.5
    use_complementarity: bool = True
    use_diversity: bool = True


@dataclass
class SelectionResult:
    """One picked item plus the score breakdown that justified it."""

    product: Product
    final_score: float
    vibe_score: float
    complementarity: float
    redundancy: float


def product_tag_categories(product: Product) -> set[str]:
    """Return the set of tag categories that show up in a product's text.

    Uses the same vocabulary-driven extractor that the image pipeline uses,
    so image tags and product tags share the same category space.
    """
    text = product.encode_text()
    if not text.strip():
        return set()
    try:
        tags = extract_structured_tags(text)
    except TagExtractionError:
        return set()
    return {tag.category for tag in tags}


def select_items(
    candidate_scores: list[float],
    candidate_embeddings: np.ndarray,
    candidate_products: list[Product],
    image_tag_categories: set[str],
    top_k: int,
    *,
    config: SelectionConfig | None = None,
    coverage_fn: Callable[[Product], set[str]] | None = None,
) -> list[SelectionResult]:
    """Greedy selection over a candidate pool.

    Inputs are three aligned lists describing the candidate pool, plus the
    set of tag categories already present in the user's photo(s).

    ``coverage_fn`` is overridable so tests can plug in fixed coverages
    instead of running the real text extractor.
    """
    config = config or SelectionConfig()
    n_candidates = len(candidate_scores)
    if n_candidates == 0 or top_k <= 0:
        return []
    if candidate_embeddings.shape[0] != n_candidates or len(candidate_products) != n_candidates:
        raise ValueError("candidate_scores, embeddings, and products must align in length.")

    fn = coverage_fn or product_tag_categories
    coverage = [fn(p) for p in candidate_products]

    missing = set(TAG_CATEGORIES) - image_tag_categories
    missing_size = max(1, len(missing))

    selected: list[SelectionResult] = []
    selected_indices: set[int] = set()

    target = min(top_k, n_candidates)
    while len(selected) < target:
        best_score = -np.inf
        best_idx: int | None = None
        best_breakdown: tuple[float, float, float] = (0.0, 0.0, 0.0)

        for i in range(n_candidates):
            if i in selected_indices:
                continue

            vibe = candidate_scores[i]

            comp = 0.0
            if config.use_complementarity and missing:
                comp = len(coverage[i] & missing) / missing_size

            red = 0.0
            if config.use_diversity and selected_indices:
                cand_emb = candidate_embeddings[i]
                red = max(
                    float(np.dot(cand_emb, candidate_embeddings[j]))
                    for j in selected_indices
                )

            score = (
                config.weight_vibe * vibe
                + config.weight_complementarity * comp
                - config.weight_redundancy * red
            )

            if score > best_score:
                best_score = score
                best_idx = i
                best_breakdown = (vibe, comp, red)

        if best_idx is None:
            break

        vibe, comp, red = best_breakdown
        selected.append(
            SelectionResult(
                product=candidate_products[best_idx],
                final_score=float(best_score),
                vibe_score=float(vibe),
                complementarity=float(comp),
                redundancy=float(red),
            )
        )
        selected_indices.add(best_idx)

    return selected
