from __future__ import annotations

import numpy as np
import pytest

from vibecheck.pipeline import analyze_images
from vibecheck.rec import (
    Product,
    ProductIndex,
    RecommendationConfig,
    RedditTextIndex,
    build_query_string,
    expand_query,
    recommend_items,
)
from vibecheck.rec.encoder import l2_normalize
from helpers import StubVisionClient, make_payload


class StubEncoder:
    """Deterministic, tiny stand-in for the real fashion-bert encoder.

    Each character contributes to a fixed bucket of the output vector, then we
    L2-normalize. This is enough to give different strings different vectors so
    FAISS can rank them, without loading the real model.
    """

    DIM = 8

    @property
    def dim(self) -> int:
        return self.DIM

    def encode(self, texts, *, batch_size: int = 32, show_progress: bool = False) -> np.ndarray:
        out = np.zeros((len(texts), self.DIM), dtype=np.float32)
        for i, text in enumerate(texts):
            for ch in text.lower():
                out[i, ord(ch) % self.DIM] += 1.0
        return l2_normalize(out)


@pytest.fixture
def stub_encoder() -> StubEncoder:
    return StubEncoder()


@pytest.fixture
def reddit_index(stub_encoder: StubEncoder) -> RedditTextIndex:
    texts = [
        "cottagecore floral linen cozy soft natural light",
        "dark academia tweed wool study leather books",
        "y2k chrome shiny metallic bright neon vibrant",
    ]
    embs = stub_encoder.encode(texts)
    return RedditTextIndex(texts=texts, embeddings=embs)


@pytest.fixture
def product_index(stub_encoder: StubEncoder) -> ProductIndex:
    products = [
        Product(
            id="p1",
            name="Floral linen dress",
            description="Cottagecore prairie dress with soft natural fibers",
            category="Dresses",
            brand="Brand A",
            gender="f",
            price="42.00",
            product_link="https://example.com/p1",
            image_link="https://example.com/p1.jpg",
        ),
        Product(
            id="p2",
            name="Tweed academic blazer",
            description="Dark academia wool blazer with leather buttons",
            category="Outerwear",
            brand="Brand B",
            gender="u",
            price="120.00",
            product_link="https://example.com/p2",
            image_link="https://example.com/p2.jpg",
        ),
        Product(
            id="p3",
            name="Chrome y2k crossbody",
            description="Shiny metallic y2k bag with neon accents",
            category="Bags",
            brand="Brand C",
            gender="f",
            price="35.00",
            product_link="https://example.com/p3",
            image_link="https://example.com/p3.jpg",
        ),
    ]
    embs = stub_encoder.encode([p.encode_text() for p in products])
    return ProductIndex(products=products, embeddings=embs)


def test_build_query_string_concatenates_all_relevant_fields() -> None:
    payload = make_payload(
        scene_type="room",
        visual_summary="A cozy reading nook.",
        aesthetic_descriptors=["cottagecore", "rustic"],
        mood_descriptors=["calm", "homey"],
        vibe_query="warm neutrals, woven textures, natural light",
    )

    query = build_query_string(payload)

    assert "warm neutrals" in query
    assert "cottagecore" in query
    assert "calm" in query


def test_build_query_string_handles_empty_payload() -> None:
    payload = make_payload(
        scene_type="unclear",
        visual_summary="",
        vibe_query="",
    )

    assert build_query_string(payload) == ""


def test_expand_query_blends_in_neighbor_embeddings(
    stub_encoder: StubEncoder, reddit_index: RedditTextIndex
) -> None:
    query_vec = stub_encoder.encode(["cottagecore"])

    expanded = expand_query(query_vec, reddit_index, k_corpus=2, alpha=1.0, beta=0.5)

    assert expanded.shape == query_vec.shape
    # L2-normalized
    assert np.isclose(np.linalg.norm(expanded), 1.0, atol=1e-5)
    # Different from the bare query (something was blended in)
    assert not np.allclose(expanded, query_vec)


def test_expand_query_with_beta_zero_is_a_noop(
    stub_encoder: StubEncoder, reddit_index: RedditTextIndex
) -> None:
    query_vec = stub_encoder.encode(["cottagecore"])
    expanded = expand_query(query_vec, reddit_index, k_corpus=5, beta=0.0)

    assert np.allclose(expanded, query_vec)


def test_recommend_items_returns_products_for_matching_vibe(
    stub_encoder: StubEncoder,
    reddit_index: RedditTextIndex,
    product_index: ProductIndex,
) -> None:
    payload = make_payload(
        scene_type="outfit",
        visual_summary="Floral cottagecore dress with linen and soft natural light.",
        aesthetic_descriptors=["cottagecore"],
        vibe_query="floral cottagecore linen prairie",
    )

    results = recommend_items(
        payload,
        config=RecommendationConfig(top_k=3, k_corpus=2),
        encoder=stub_encoder,
        reddit_index=reddit_index,
        product_index=product_index,
    )

    # Mechanics check only: the stub encoder is not a real semantic model, so
    # we don't assert which item ranks first -- just that retrieval works,
    # returns the requested number of items, and scores them consistently.
    assert len(results) == 3
    returned_ids = [r["id"] for r in results]
    assert set(returned_ids) == {"p1", "p2", "p3"}
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    for item in results:
        assert isinstance(item["score"], float)
        assert "name" in item
        assert "image_url" in item


def test_recommend_items_returns_empty_for_empty_payload(
    stub_encoder: StubEncoder,
    reddit_index: RedditTextIndex,
    product_index: ProductIndex,
) -> None:
    payload = make_payload(scene_type="unclear", visual_summary="", vibe_query="")

    results = recommend_items(
        payload,
        encoder=stub_encoder,
        reddit_index=reddit_index,
        product_index=product_index,
    )

    assert results == []


def test_pipeline_skips_recommendations_by_default(room_payload) -> None:
    """analyze_images() must not load the rec module unless asked to."""
    client = StubVisionClient(room_payload)

    result = analyze_images([b"\xff\xd8\xfffake"], mode="room", client=client)

    assert result.item_recommendations == []
    assert "recommend_items" not in result.debug.timings_ms


def test_pipeline_attaches_recommendations_when_flag_set(
    monkeypatch: pytest.MonkeyPatch, room_payload
) -> None:
    """analyze_images(with_recommendations=True) calls into the rec module."""
    captured: dict[str, object] = {}

    def fake_recommend_items(payload, *, config=None):
        captured["payload"] = payload
        captured["config"] = config
        return [{"id": "stub", "name": "stub", "score": 0.9}]

    import vibecheck.rec as rec_module

    monkeypatch.setattr(rec_module, "recommend_items", fake_recommend_items)

    client = StubVisionClient(room_payload)
    result = analyze_images(
        [b"\xff\xd8\xfffake"],
        mode="room",
        client=client,
        with_recommendations=True,
        recommend_top_k=4,
    )

    assert result.item_recommendations == [{"id": "stub", "name": "stub", "score": 0.9}]
    assert captured["config"].top_k == 4
    assert "recommend_items" in result.debug.timings_ms
