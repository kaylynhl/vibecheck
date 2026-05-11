"""Tests for the live-Spotify track recommender.

We never hit the real Spotify API in CI -- the ``SpotifyClient`` is replaced
with a stub that returns canned track dicts. This isolates the unit under
test (query building, deduping, fashion-bert re-ranking, graceful failure)
from any network or rate-limit flakiness.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from vibecheck.errors import ConfigurationError
from vibecheck.rec.playlists import (
    DEFAULT_RESULTS_PER_QUERY,
    Track,
    build_search_queries,
    normalize_track,
    recommend_tracks,
)
from vibecheck.rec.spotify_client import SpotifyClient
from helpers import make_payload
from test_recommend import StubEncoder


# ---- fixtures ----------------------------------------------------------------


class StubSpotify(SpotifyClient):
    """In-memory Spotify client that returns pre-canned results per query."""

    def __init__(self, results_by_query: dict[str, list[dict[str, Any]]]) -> None:
        super().__init__(client_id="stub", client_secret="stub")
        self.results_by_query = results_by_query
        self.calls: list[tuple[str, int]] = []

    def search_tracks(  # type: ignore[override]
        self,
        query: str,
        *,
        limit: int = 50,
        market: str | None = None,
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        self.calls.append((query, limit))
        return list(self.results_by_query.get(query, []))


def make_raw_track(track_id: str, name: str, artist: str) -> dict[str, Any]:
    """Mimic the shape of a Spotify Web API track object."""
    return {
        "id": track_id,
        "name": name,
        "artists": [{"name": artist}],
        "album": {
            "name": f"{name} (Album)",
            "images": [{"url": f"https://img.example/{track_id}.jpg"}],
        },
        "preview_url": f"https://preview.example/{track_id}.mp3",
        "external_urls": {"spotify": f"https://open.spotify.com/track/{track_id}"},
        "duration_ms": 200000,
    }


@pytest.fixture
def stub_encoder() -> StubEncoder:
    return StubEncoder()


# ---- pure-function tests -----------------------------------------------------


def test_build_search_queries_dedupes_and_caps() -> None:
    payload = make_payload(
        scene_type="outfit",
        visual_summary="x",
        aesthetic_descriptors=["cottagecore", "rustic", "cottagecore", "soft"],
        mood_descriptors=["calm", "warm"],
        vibe_query="cottagecore, floral, linen",
    )

    queries = build_search_queries(payload, max_queries=4)

    assert "cottagecore" in queries
    assert "rustic" in queries
    assert len(queries) == len(set(queries))
    assert len(queries) <= 4


def test_build_search_queries_empty_payload_returns_empty() -> None:
    payload = make_payload(scene_type="unclear", visual_summary="", vibe_query="")
    assert build_search_queries(payload) == []


def test_build_search_queries_strips_punctuation() -> None:
    payload = make_payload(
        scene_type="outfit",
        visual_summary="x",
        aesthetic_descriptors=["cottage/core?", "y2k!"],
        vibe_query="",
    )
    queries = build_search_queries(payload)
    assert all("?" not in q and "!" not in q for q in queries)


def test_normalize_track_keeps_useful_fields() -> None:
    raw = make_raw_track("abc", "Heather", "Conan Gray")

    track = normalize_track(raw)

    assert isinstance(track, Track)
    assert track.spotify_id == "abc"
    assert track.name == "Heather"
    assert track.artists == ["Conan Gray"]
    assert track.spotify_url.endswith("/abc")
    assert track.album_image is not None
    out = track.to_dict(score=0.42)
    assert out["score"] == 0.42
    assert out["preview_url"].endswith(".mp3")


def test_normalize_track_drops_malformed() -> None:
    assert normalize_track({}) is None
    assert normalize_track({"id": "x"}) is None
    assert normalize_track({"name": "x"}) is None


# ---- end-to-end recommend_tracks tests --------------------------------------


def test_recommend_tracks_fetches_dedupes_and_returns_top_k(
    stub_encoder: StubEncoder,
) -> None:
    payload = make_payload(
        scene_type="outfit",
        visual_summary="cottagecore floral",
        aesthetic_descriptors=["cottagecore", "rustic"],
        vibe_query="cottagecore, floral, linen",
    )

    spotify = StubSpotify(
        results_by_query={
            "cottagecore": [
                make_raw_track("a", "Heather", "Conan Gray"),
                make_raw_track("b", "Cardigan", "Taylor Swift"),
            ],
            "rustic": [
                make_raw_track("b", "Cardigan", "Taylor Swift"),  # dup with above
                make_raw_track("c", "Ophelia", "The Lumineers"),
            ],
        }
    )

    results = recommend_tracks(
        payload,
        top_k=3,
        encoder=stub_encoder,
        spotify=spotify,
        use_query_expansion=False,
    )

    assert len(results) == 3
    ids = {r["spotify_id"] for r in results}
    assert ids == {"a", "b", "c"}
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert len(spotify.calls) >= 2  # at least the two non-empty queries


def test_recommend_tracks_truncates_to_top_k(stub_encoder: StubEncoder) -> None:
    payload = make_payload(
        scene_type="outfit",
        visual_summary="x",
        aesthetic_descriptors=["folk"],
        vibe_query="folk",
    )
    spotify = StubSpotify(
        results_by_query={
            "folk": [make_raw_track(f"id{i}", f"track{i}", "artist") for i in range(8)]
        }
    )

    results = recommend_tracks(
        payload, top_k=4, encoder=stub_encoder, spotify=spotify, use_query_expansion=False
    )

    assert len(results) == 4


def test_recommend_tracks_returns_empty_for_empty_payload(
    stub_encoder: StubEncoder,
) -> None:
    payload = make_payload(scene_type="unclear", visual_summary="", vibe_query="")
    spotify = StubSpotify(results_by_query={})

    results = recommend_tracks(
        payload, top_k=5, encoder=stub_encoder, spotify=spotify
    )

    assert results == []
    assert spotify.calls == []  # never reached Spotify


def test_recommend_tracks_handles_no_search_results(stub_encoder: StubEncoder) -> None:
    payload = make_payload(
        scene_type="outfit",
        visual_summary="x",
        aesthetic_descriptors=["nonexistent"],
        vibe_query="nonexistent",
    )
    spotify = StubSpotify(results_by_query={})

    results = recommend_tracks(
        payload, top_k=5, encoder=stub_encoder, spotify=spotify
    )

    assert results == []


def test_recommend_tracks_accepts_explicit_queries(stub_encoder: StubEncoder) -> None:
    payload = make_payload(
        scene_type="outfit",
        visual_summary="anything",
        vibe_query="anything",
    )
    spotify = StubSpotify(
        results_by_query={"manual": [make_raw_track("z", "Zed", "Zee")]}
    )

    results = recommend_tracks(
        payload,
        top_k=1,
        encoder=stub_encoder,
        spotify=spotify,
        queries=["manual"],
        use_query_expansion=False,
    )

    assert len(results) == 1
    assert results[0]["spotify_id"] == "z"
    assert spotify.calls == [("manual", DEFAULT_RESULTS_PER_QUERY)]


def test_recommend_tracks_passes_query_through_encoder(
    stub_encoder: StubEncoder,
) -> None:
    """Track text should actually be encoded by the encoder we passed in."""
    payload = make_payload(
        scene_type="outfit",
        visual_summary="x",
        aesthetic_descriptors=["folk"],
        vibe_query="folk",
    )
    spotify = StubSpotify(
        results_by_query={
            "folk": [
                make_raw_track("a", "Cottagecore Linen Folk", "Folk Artist"),
                make_raw_track("b", "Chrome Y2K Bass", "Cyber Artist"),
            ]
        }
    )

    results = recommend_tracks(
        payload,
        top_k=2,
        encoder=stub_encoder,
        spotify=spotify,
        use_query_expansion=False,
    )

    assert len(results) == 2
    # The stub encoder differentiates by character buckets, so the two
    # tracks should not get identical scores.
    assert results[0]["score"] != results[1]["score"]


# ---- Spotify client behavior under failure ----------------------------------


def test_spotify_client_raises_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    client = SpotifyClient()

    with pytest.raises(ConfigurationError):
        client._ensure_credentials()


def test_spotify_client_empty_query_short_circuits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty queries must not even attempt a token fetch."""
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "stub")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "stub")
    client = SpotifyClient()

    def boom(*args, **kwargs):  # would explode if called
        raise AssertionError("Should not have hit the network for an empty query")

    monkeypatch.setattr(client, "_fetch_token", boom)
    assert client.search_tracks("") == []
    assert client.search_tracks("   ") == []
