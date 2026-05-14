"""Vibe-to-playlist recommendation: generate a playlist of real Spotify tracks
for an inferred vibe.

We can no longer use Spotify's ``/v1/recommendations`` endpoint (deprecated
for new developer apps as of Nov 27, 2024), so the pipeline is:

    photo -> vibe payload -> N search queries -> Spotify /search?type=track
        -> dedupe pool -> fashion-bert re-rank against the expanded vibe
        query -> top-K tracks returned to the caller

Spotify is the *catalog*; our fashion-bert encoder is the *ranker*. This
keeps the "our model picks the songs" claim intact for the writeup while
working around the API constraint.

The ``recommend_tracks`` entry point is intended to be called from a
long-running backend process (the FastAPI server in Step 8). The Spotify
client caches its access token in-process so we only authenticate once
per hour, not once per request.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from vibecheck.errors import VibecheckError
from vibecheck.rec.encoder import FashionBertEncoder, l2_normalize
from vibecheck.rec.expansion import expand_query
from vibecheck.rec.recommend import build_query_string
from vibecheck.rec.spotify_client import SpotifyClient, get_default_client
from vibecheck.rec.text_index import RedditTextIndex


MAX_QUERIES_PER_REQUEST = 8
# Spotify's /v1/search rejects limit > 10 with HTTP 400 "Invalid limit" when
# called with a new-app Client Credentials token, despite the docs claiming
# the range is 0-50. We cap at 10 and run more queries to compensate.
DEFAULT_RESULTS_PER_QUERY = 10
SPOTIFY_MAX_LIMIT = 10


@dataclass
class Track:
    """One Spotify track normalized down to the fields the mobile app renders."""

    spotify_id: str
    name: str
    artists: list[str]
    album_name: str | None
    album_image: str | None
    preview_url: str | None
    spotify_url: str | None
    duration_ms: int | None

    def encode_text(self) -> str:
        """Text used to compute this track's fashion-bert embedding.

        We feed ``"<title> - <artist>"`` because Spotify search relevance is
        dominated by track title, and artist names supply a useful extra
        signal when multiple covers / versions share a title.
        """
        artist = ", ".join(self.artists) if self.artists else ""
        return f"{self.name} - {artist}".strip(" -")

    def to_dict(self, score: float | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {
            "spotify_id": self.spotify_id,
            "name": self.name,
            "artists": list(self.artists),
            "album_name": self.album_name,
            "album_image": self.album_image,
            "preview_url": self.preview_url,
            "spotify_url": self.spotify_url,
            "duration_ms": self.duration_ms,
        }
        if score is not None:
            out["score"] = round(float(score), 4)
        return out


def normalize_track(raw: dict[str, Any]) -> Track | None:
    """Map a raw Spotify track object to a Track, dropping malformed entries."""
    if not isinstance(raw, dict) or not raw.get("id") or not raw.get("name"):
        return None
    album = raw.get("album") or {}
    images = album.get("images") or []
    external = raw.get("external_urls") or {}
    artists = [a.get("name") for a in (raw.get("artists") or []) if a and a.get("name")]
    return Track(
        spotify_id=raw["id"],
        name=raw["name"],
        artists=artists,
        album_name=album.get("name"),
        album_image=images[0]["url"] if images else None,
        preview_url=raw.get("preview_url"),
        spotify_url=external.get("spotify"),
        duration_ms=raw.get("duration_ms"),
    )


def build_search_queries(payload, *, max_queries: int = MAX_QUERIES_PER_REQUEST) -> list[str]:
    """Translate a vision payload into a small list of Spotify search queries.

    Spotify's search relevance is keyword-driven, so we use short noun-phrase
    style queries rather than the long comma-joined string we feed our own
    encoder. We pull terms from the payload's aesthetic descriptors, the
    individual comma-separated chunks of ``vibe_query``, and the mood
    descriptors -- this widens the candidate pool, which matters because
    Spotify caps ``limit`` at 10 per call for new apps.

    Returns a deduplicated, ordered list capped at ``max_queries``.
    """
    queries: list[str] = []

    def add(value: str) -> None:
        cleaned = re.sub(r"[^\w\s,-]", " ", value).strip().lower()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if not cleaned or len(cleaned) < 2:
            return
        if cleaned not in queries:
            queries.append(cleaned)

    if payload is None:
        return queries

    for descriptor in (payload.aesthetic_descriptors or [])[:4]:
        add(descriptor)

    if getattr(payload, "vibe_query", None):
        for chunk in payload.vibe_query.split(",")[:3]:
            add(chunk)

    for descriptor in (payload.mood_descriptors or [])[:3]:
        add(descriptor)

    return queries[:max_queries]


def _rerank_with_encoder(
    tracks: list[Track],
    payload,
    *,
    encoder: FashionBertEncoder,
    reddit_index: RedditTextIndex | None,
    use_query_expansion: bool,
) -> list[tuple[float, Track]]:
    """Encode each track's title+artist and rank by cosine to the vibe query.

    When ``reddit_index`` is provided we run the same Reddit-driven query
    expansion that powers the item recommender, so the ranking benefits from
    aesthetic vocabulary the encoder picked up during fine-tuning.
    """
    query = build_query_string(payload)
    if not query or not tracks:
        return [(0.0, t) for t in tracks]

    query_vec = encoder.encode([query])
    if use_query_expansion and reddit_index is not None:
        query_vec = expand_query(query_vec, reddit_index)
    query_vec = l2_normalize(query_vec)

    track_texts = [t.encode_text() for t in tracks]
    track_vecs = l2_normalize(encoder.encode(track_texts))

    scores = (track_vecs @ query_vec[0]).astype(np.float32)
    pairs = list(zip(scores.tolist(), tracks))
    pairs.sort(key=lambda kv: -kv[0])
    return pairs


def recommend_tracks(
    payload,
    *,
    top_k: int = 20,
    results_per_query: int = DEFAULT_RESULTS_PER_QUERY,
    encoder: FashionBertEncoder | None = None,
    spotify: SpotifyClient | None = None,
    reddit_index: RedditTextIndex | None = None,
    use_query_expansion: bool = True,
    market: str | None = None,
    queries: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Generate a playlist of real Spotify tracks matching the vibe payload.

    Args:
        payload: Vision payload from ``analyze_images``. Used to build search
            queries and the re-ranking query.
        top_k: Number of tracks to return.
        results_per_query: How many tracks to ask Spotify for per query
            (max 50). Higher widens the candidate pool we re-rank.
        encoder: Optional fashion-bert encoder. Falls back to a process-wide
            singleton if omitted.
        spotify: Optional Spotify client. Falls back to a process-wide
            singleton (which reads credentials from env on first use).
        reddit_index: Optional Reddit FAISS index. When provided, the
            re-ranking query is expanded the same way as item retrieval.
        use_query_expansion: Toggle for the above. Defaults to True.
        market: Optional ISO-3166-1 market code for Spotify search.
        queries: Optional override; if passed, we skip ``build_search_queries``.

    Returns:
        A list of track dicts (see ``Track.to_dict``) ordered by descending
        fashion-bert similarity to the (optionally expanded) vibe query.
        Empty list on any failure -- the caller (pipeline) wraps this in a
        try/except and degrades gracefully.
    """
    search_queries = list(queries) if queries is not None else build_search_queries(payload)
    if not search_queries:
        return []

    spotify = spotify or get_default_client()

    seen: dict[str, Track] = {}
    for query in search_queries:
        try:
            raw_items = spotify.search_tracks(
                query, limit=results_per_query, market=market
            )
        except VibecheckError:
            # Configuration / credential errors are fatal; let them surface
            # so the pipeline can warn the user.
            raise
        for raw in raw_items:
            track = normalize_track(raw)
            if track and track.spotify_id not in seen:
                seen[track.spotify_id] = track

    if not seen:
        return []

    encoder = encoder or _shared_encoder()
    ranked = _rerank_with_encoder(
        list(seen.values()),
        payload,
        encoder=encoder,
        reddit_index=reddit_index,
        use_query_expansion=use_query_expansion,
    )

    # Second dedupe pass: Spotify's catalog often has multiple IDs for what
    # is, for our purposes, the same song (album vs single, explicit vs
    # clean, regional re-releases, "feat." variants, etc.). The first dedupe
    # above only catches exact-ID collisions, which is why the same track
    # by the same artist can appear 3-4 times in the final playlist. We
    # collapse those by (lowercased title, sorted lowercased artists) here,
    # *after* re-ranking, so we keep the highest-scoring variant.
    deduped: list[tuple[float, Track]] = []
    seen_keys: set[tuple[str, tuple[str, ...]]] = set()
    for score, track in ranked:
        title = (track.name or "").strip().lower()
        artists = tuple(
            sorted(a.strip().lower() for a in (track.artists or []) if a)
        )
        key = (title, artists)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append((score, track))

    return [track.to_dict(score=score) for score, track in deduped[:top_k]]


# Process-wide encoder singleton so repeated requests don't reload the model.
_ENCODER: FashionBertEncoder | None = None


def _shared_encoder() -> FashionBertEncoder:
    global _ENCODER
    if _ENCODER is None:
        _ENCODER = FashionBertEncoder()
    return _ENCODER


def reset_shared_state() -> None:
    """Drop the encoder singleton. Only useful for tests."""
    global _ENCODER
    _ENCODER = None
