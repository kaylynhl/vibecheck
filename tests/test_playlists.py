"""Tests for the playlist recommendation path.

We avoid loading the real fashion-bert model or hitting disk by reusing the
``StubEncoder`` from ``test_recommend`` and building an in-memory
``PlaylistIndex``.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from vibecheck.rec.encoder import l2_normalize
from vibecheck.rec.playlists import (
    Playlist,
    PlaylistIndex,
    load_playlist_index,
    load_playlists_from_csv,
    load_playlists_from_seed,
    recommend_playlist,
)
from tests.helpers import make_payload
from tests.test_recommend import StubEncoder


@pytest.fixture
def stub_encoder() -> StubEncoder:
    return StubEncoder()


@pytest.fixture
def playlist_index(stub_encoder: StubEncoder) -> PlaylistIndex:
    playlists = [
        Playlist(title="Cottagecore mornings: soft folk and pressed flowers", aesthetic="cottagecore"),
        Playlist(title="Y2K bops: bubblegum pop and chrome shine", aesthetic="y2k"),
        Playlist(title="Cyberpunk neon nights: synthwave and industrial", aesthetic="cyberpunk"),
    ]
    embs = stub_encoder.encode([p.encode_text() for p in playlists])
    return PlaylistIndex(playlists=playlists, embeddings=embs)


def test_playlist_to_dict_strips_none_fields() -> None:
    pl = Playlist(title="Test")
    out = pl.to_dict(score=0.5)
    assert out == {"title": "Test", "score": 0.5}


def test_playlist_to_dict_keeps_populated_fields() -> None:
    pl = Playlist(title="Test", aesthetic="y2k", curator="me", url="https://x")
    out = pl.to_dict()
    assert out == {
        "title": "Test",
        "aesthetic": "y2k",
        "curator": "me",
        "url": "https://x",
    }


def test_index_search_returns_requested_count(
    stub_encoder: StubEncoder, playlist_index: PlaylistIndex
) -> None:
    query = stub_encoder.encode(["cottagecore floral soft folk"])

    results = playlist_index.search(query, k=2)

    assert len(results) == 2
    assert all(isinstance(score, float) for score, _ in results)
    assert all(isinstance(p, Playlist) for _, p in results)
    scores = [s for s, _ in results]
    assert scores == sorted(scores, reverse=True)


def test_recommend_playlist_uses_explicit_query(
    stub_encoder: StubEncoder, playlist_index: PlaylistIndex
) -> None:
    results = recommend_playlist(
        payload=None,
        top_k=3,
        encoder=stub_encoder,
        playlist_index=playlist_index,
        query="cottagecore soft folk warm folk",
    )

    assert len(results) == 3
    assert all("title" in r for r in results)
    titles = {r["title"] for r in results}
    assert any("Cottagecore" in t for t in titles)


def test_recommend_playlist_empty_for_empty_payload(
    stub_encoder: StubEncoder, playlist_index: PlaylistIndex
) -> None:
    payload = make_payload(scene_type="unclear", visual_summary="", vibe_query="")
    results = recommend_playlist(
        payload, top_k=3, encoder=stub_encoder, playlist_index=playlist_index
    )
    assert results == []


def test_recommend_playlist_builds_query_from_payload(
    stub_encoder: StubEncoder, playlist_index: PlaylistIndex
) -> None:
    payload = make_payload(
        scene_type="outfit",
        visual_summary="cottagecore",
        vibe_query="floral cottagecore linen prairie",
    )
    results = recommend_playlist(
        payload, top_k=2, encoder=stub_encoder, playlist_index=playlist_index
    )
    assert len(results) == 2


def test_load_playlists_from_seed_uses_bundled_file() -> None:
    playlists = load_playlists_from_seed()
    assert len(playlists) >= 50
    aesthetics = {p.aesthetic for p in playlists if p.aesthetic}
    assert "cottagecore" in aesthetics
    assert "streetwear" in aesthetics
    assert "y2k" in aesthetics


def test_load_playlists_from_csv_normalizes_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "playlists.csv"
    csv_path.write_text(
        "user_id,playlistname,extra\n"
        "alice,Cottagecore mornings,foo\n"
        "bob,Y2K bops,bar\n"
        "alice,Cottagecore mornings,foo\n",
        encoding="utf-8",
    )

    playlists = load_playlists_from_csv(csv_path)

    titles = [p.title for p in playlists]
    assert titles == ["Cottagecore mornings", "Y2K bops"]
    assert playlists[0].curator == "alice"


def test_load_playlist_index_falls_back_to_seed_when_csv_missing(
    tmp_path: Path, stub_encoder: StubEncoder
) -> None:
    """With no source CSV and no cached embeddings, the loader uses the seed set."""
    seed_path = tmp_path / "seed.json"
    seed_path.write_text(
        json.dumps(
            [
                {"title": "Cottagecore mornings", "aesthetic": "cottagecore"},
                {"title": "Y2K bops", "aesthetic": "y2k"},
            ]
        ),
        encoding="utf-8",
    )

    index = load_playlist_index(
        encoder=stub_encoder,
        seed_path=seed_path,
        cache_path=tmp_path / "cache.npy",
        source_csv=tmp_path / "missing.csv",
    )

    assert len(index.playlists) == 2
    assert index.embeddings.shape == (2, stub_encoder.dim)


def test_load_playlist_index_uses_cache_when_count_matches(
    tmp_path: Path, stub_encoder: StubEncoder
) -> None:
    seed_path = tmp_path / "seed.json"
    seed_path.write_text(
        json.dumps([{"title": "Cottagecore mornings", "aesthetic": "cottagecore"}]),
        encoding="utf-8",
    )
    cache_path = tmp_path / "cache.npy"
    cached = l2_normalize(np.ones((1, stub_encoder.dim), dtype=np.float32))
    np.save(cache_path, cached)

    index = load_playlist_index(
        encoder=stub_encoder,
        seed_path=seed_path,
        cache_path=cache_path,
        source_csv=tmp_path / "missing.csv",
    )

    np.testing.assert_allclose(index.embeddings, cached)
