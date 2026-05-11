"""Unit tests for the greedy selection step.

We exercise the score formula and ablation flags directly with synthetic
embeddings + a fake coverage function, so the test never touches sentence
transformers, FAISS, or the real tag extractor.
"""

from __future__ import annotations

import numpy as np
import pytest

from vibecheck.rec import (
    Product,
    ProductIndex,
    RecommendationConfig,
    SelectionConfig,
    recommend_items,
    select_items,
)
from vibecheck.rec.encoder import l2_normalize
from vibecheck.rec.select import SelectionResult


def make_product(pid: str, name: str = "x", description: str = "x") -> Product:
    return Product(
        id=pid,
        name=name,
        description=description,
        category="cat",
        brand="brand",
        gender="u",
        price="10.00",
        product_link="",
        image_link="",
    )


def normed(vec: list[float]) -> np.ndarray:
    arr = np.array([vec], dtype=np.float32)
    return l2_normalize(arr)[0]


def stack(rows: list[np.ndarray]) -> np.ndarray:
    return np.stack(rows).astype(np.float32)


def test_select_returns_top_k_results() -> None:
    products = [make_product(f"p{i}") for i in range(5)]
    embeddings = stack([normed([1.0, float(i)]) for i in range(5)])
    scores = [0.5, 0.4, 0.3, 0.2, 0.1]

    results = select_items(scores, embeddings, products, set(), top_k=3)

    assert len(results) == 3
    assert all(isinstance(r, SelectionResult) for r in results)


def test_select_with_no_diversity_no_complementarity_matches_score_order() -> None:
    """With both diversity and complementarity disabled, selection is just argmax-by-vibe."""
    products = [make_product(f"p{i}") for i in range(4)]
    embeddings = stack([normed([1.0, float(i)]) for i in range(4)])
    scores = [0.1, 0.9, 0.5, 0.7]

    results = select_items(
        scores,
        embeddings,
        products,
        set(),
        top_k=4,
        config=SelectionConfig(use_diversity=False, use_complementarity=False),
    )

    assert [r.product.id for r in results] == ["p1", "p3", "p2", "p0"]


def test_diversity_penalizes_clones() -> None:
    """Two near-identical embeddings should not both end up in the top-2."""
    products = [
        make_product("twin_a"),
        make_product("twin_b"),
        make_product("different"),
    ]
    embeddings = stack(
        [
            normed([1.0, 0.0]),
            normed([1.0, 0.0]),
            normed([0.0, 1.0]),
        ]
    )
    # twin_a and twin_b have higher vibe scores than `different`.
    scores = [0.9, 0.85, 0.5]

    diverse = select_items(
        scores,
        embeddings,
        products,
        set(),
        top_k=2,
        config=SelectionConfig(
            use_diversity=True,
            use_complementarity=False,
            weight_redundancy=1.0,
        ),
    )
    plain = select_items(
        scores,
        embeddings,
        products,
        set(),
        top_k=2,
        config=SelectionConfig(use_diversity=False, use_complementarity=False),
    )

    assert {r.product.id for r in plain} == {"twin_a", "twin_b"}
    diverse_ids = {r.product.id for r in diverse}
    assert "twin_a" in diverse_ids
    assert "different" in diverse_ids
    assert "twin_b" not in diverse_ids


def test_complementarity_prefers_items_filling_missing_categories() -> None:
    """A weaker-vibe item that fills a missing category beats a stronger-vibe item that doesn't."""
    products = [make_product("strong_redundant"), make_product("weak_complementary")]
    embeddings = stack([normed([1.0, 0.0]), normed([0.0, 1.0])])
    scores = [0.80, 0.65]

    image_categories = {"palette", "lighting", "texture", "pattern"}

    def coverage_fn(product: Product) -> set[str]:
        if product.id == "strong_redundant":
            return {"palette"}
        if product.id == "weak_complementary":
            return {"silhouette"}
        return set()

    no_comp = select_items(
        scores,
        embeddings,
        products,
        image_categories,
        top_k=1,
        config=SelectionConfig(use_complementarity=False, use_diversity=False),
        coverage_fn=coverage_fn,
    )
    with_comp = select_items(
        scores,
        embeddings,
        products,
        image_categories,
        top_k=1,
        config=SelectionConfig(
            use_complementarity=True,
            use_diversity=False,
            weight_complementarity=1.0,
        ),
        coverage_fn=coverage_fn,
    )

    assert no_comp[0].product.id == "strong_redundant"
    assert with_comp[0].product.id == "weak_complementary"
    assert with_comp[0].complementarity > 0


def test_select_handles_top_k_larger_than_pool() -> None:
    products = [make_product("p0"), make_product("p1")]
    embeddings = stack([normed([1.0, 0.0]), normed([0.0, 1.0])])
    scores = [0.5, 0.4]

    results = select_items(scores, embeddings, products, set(), top_k=10)

    assert len(results) == 2


def test_select_handles_empty_input() -> None:
    embeddings = np.zeros((0, 4), dtype=np.float32)
    assert select_items([], embeddings, [], set(), top_k=5) == []


def test_select_validates_aligned_lengths() -> None:
    products = [make_product("p0"), make_product("p1")]
    embeddings = stack([normed([1.0, 0.0])])  # mismatched length
    with pytest.raises(ValueError):
        select_items([0.5, 0.4], embeddings, products, set(), top_k=2)


# --- end-to-end through recommend_items -----------------------------------------


@pytest.fixture
def stub_encoder():
    from tests.test_recommend import StubEncoder

    return StubEncoder()


@pytest.fixture
def reddit_index(stub_encoder):
    from vibecheck.rec import RedditTextIndex

    texts = ["floral cottagecore linen", "y2k chrome metallic"]
    return RedditTextIndex(texts=texts, embeddings=stub_encoder.encode(texts))


@pytest.fixture
def product_index(stub_encoder):
    products = [
        make_product("p1", name="Floral linen dress", description="cottagecore prairie"),
        make_product("p2", name="Floral linen blouse", description="cottagecore prairie soft"),
        make_product("p3", name="Chrome y2k bag", description="shiny metallic"),
    ]
    embs = stub_encoder.encode([p.encode_text() for p in products])
    return ProductIndex(products=products, embeddings=embs)


def test_recommend_items_with_selection_attaches_breakdown(
    stub_encoder, reddit_index, product_index
) -> None:
    from tests.helpers import make_payload

    payload = make_payload(
        scene_type="outfit",
        visual_summary="Floral cottagecore prairie linen dress",
        vibe_query="floral cottagecore linen prairie",
    )

    results = recommend_items(
        payload,
        config=RecommendationConfig(
            top_k=2,
            k_corpus=2,
            candidate_pool_size=3,
            selection=SelectionConfig(),
        ),
        encoder=stub_encoder,
        reddit_index=reddit_index,
        product_index=product_index,
    )

    assert len(results) == 2
    for item in results:
        assert "selection" in item
        breakdown = item["selection"]
        assert {"vibe_score", "complementarity", "redundancy"} <= breakdown.keys()
        assert isinstance(breakdown["vibe_score"], float)


def test_recommend_items_without_selection_has_no_breakdown(
    stub_encoder, reddit_index, product_index
) -> None:
    from tests.helpers import make_payload

    payload = make_payload(
        scene_type="outfit",
        visual_summary="Floral cottagecore prairie linen dress",
        vibe_query="floral cottagecore linen prairie",
    )

    results = recommend_items(
        payload,
        config=RecommendationConfig(top_k=2, k_corpus=2),
        encoder=stub_encoder,
        reddit_index=reddit_index,
        product_index=product_index,
    )

    assert len(results) == 2
    for item in results:
        assert "selection" not in item
