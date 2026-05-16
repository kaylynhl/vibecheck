"""Vibe-to-playlist recommendation: generate a playlist of real Spotify tracks
for an inferred vibe.

The catalog is a static 1.16M-track Kaggle dataset (the live Spotify
``/v1/recommendations`` endpoint was deprecated for new apps on Nov 27 2024
and ``/v1/search`` clamps ``limit`` to 10 on Client Credentials tokens, so
the live API is no longer a viable backbone for a real recommender). The
pipeline is:

    photo -> vibe payload -> N keyword queries -> local catalog search
        -> dedupe pool -> fashion-bert *text* re-rank against the expanded
        vibe query -> audio-feature *re-rank* against the aesthetic's
        hand-crafted audio profile (with visual-tag nudges from the image)
        -> top-K tracks returned to the caller

The catalog and audio features come from the Kaggle CSV; our FashionBERT
encoder remains the primary ranker. The audio re-rank is a secondary
signal that biases the order toward tracks that *acoustically* match the
predicted aesthetic, not just textually.

The ``recommend_tracks`` entry point is intended to be called from a
long-running backend process (the FastAPI server). The local catalog is
loaded into memory once on first call and reused thereafter.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from vibecheck.errors import VibecheckError
from vibecheck.rec.encoder import FashionBertEncoder, l2_normalize
from vibecheck.rec.expansion import expand_query
from vibecheck.rec.local_catalog import LocalCatalogClient, get_default_local_client
from vibecheck.rec.recommend import build_query_string
from vibecheck.rec.spotify_audio import audio_score
from vibecheck.rec.text_index import RedditTextIndex
from vibecheck.schemas import ExtractedTag


MAX_QUERIES_PER_REQUEST = 8
# Local catalog has no rate limit or per-query cap, so we widen the pool
# per query. The text + audio re-rankers downstream can absorb a larger
# candidate set without latency issues.
DEFAULT_RESULTS_PER_QUERY = 50
# Audio-feature candidate pool size: aesthetic labels like "dark academia"
# rarely appear in track metadata, so keyword search often returns very few
# matches. We backfill the candidate pool with the top tracks by audio
# similarity over the entire catalog so the re-rankers always have material.
DEFAULT_AUDIO_POOL_SIZE = 200
# Weight applied to the audio-feature similarity when combining with the
# FashionBERT text similarity: final_score = text + AUDIO_LAMBDA * audio.
# Text dominates by design (it carries more semantic signal); audio is a
# tie-breaker that biases toward acoustically appropriate tracks.
DEFAULT_AUDIO_LAMBDA = 0.3


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
    audio_features: dict[str, float] | None = None
    genre: str | None = None

    def encode_text(self) -> str:
        """Text used to compute this track's fashion-bert embedding.

        We feed ``"<title> - <artist> (<genre>)"`` (genre only when known).
        Title + artist alone is not enough to separate, say, a grunge track
        from an EDM track when both happen to have similar energy / loudness
        / acousticness -- which is exactly the failure case the audio-feature
        candidate filter produces. Adding the genre token gives the FashionBERT
        re-ranker a real lever to push the right tracks up.
        """
        artist = ", ".join(self.artists) if self.artists else ""
        base = f"{self.name} - {artist}".strip(" -")
        if self.genre:
            return f"{base} ({self.genre})"
        return base

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
        if self.audio_features:
            out["audio_features"] = dict(self.audio_features)
        if self.genre:
            out["genre"] = self.genre
        if score is not None:
            out["score"] = round(float(score), 4)
        return out


def normalize_track(raw: dict[str, Any]) -> Track | None:
    """Map a raw Spotify-shaped track object to a Track, dropping malformed entries.

    Accepts both real Spotify Web API JSON and the dicts returned by
    :class:`vibecheck.rec.local_catalog.LocalCatalogClient`. The local
    client adds an extra ``audio_features`` key that we pull through; for
    real Spotify responses that field is simply absent and we leave
    ``Track.audio_features`` as None.
    """
    if not isinstance(raw, dict) or not raw.get("id") or not raw.get("name"):
        return None
    album = raw.get("album") or {}
    images = album.get("images") or []
    external = raw.get("external_urls") or {}
    artists = [a.get("name") for a in (raw.get("artists") or []) if a and a.get("name")]
    audio = raw.get("audio_features")
    if audio is not None and not isinstance(audio, dict):
        audio = None
    genre = raw.get("genre")
    if genre is not None and not isinstance(genre, str):
        genre = None
    return Track(
        spotify_id=raw["id"],
        name=raw["name"],
        artists=artists,
        album_name=album.get("name"),
        album_image=images[0]["url"] if images else None,
        preview_url=raw.get("preview_url"),
        spotify_url=external.get("spotify"),
        duration_ms=raw.get("duration_ms"),
        audio_features=audio,
        genre=genre or None,
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


def _top_aesthetic(payload) -> str:
    """Pick the single aesthetic to use for audio profile lookup."""
    descriptors = getattr(payload, "aesthetic_descriptors", None) or []
    for d in descriptors:
        if d and d.strip():
            return d
    return ""


def _combine_text_and_audio(
    text_ranked: list[tuple[float, Track]],
    *,
    aesthetic: str,
    image_tags: Iterable[ExtractedTag] | None,
    audio_lambda: float,
) -> list[tuple[float, Track]]:
    """Add an audio-feature similarity to each text score, then re-sort.

    The combined score is ``text + audio_lambda * audio``. Tracks without
    audio features (e.g. when the catalog client doesn't supply them) get
    ``audio = 0``, so they fall back to text-only behaviour cleanly.
    """
    if audio_lambda <= 0 or not aesthetic:
        return text_ranked
    tags = list(image_tags) if image_tags is not None else None
    combined: list[tuple[float, Track]] = []
    for text_s, track in text_ranked:
        a = audio_score(track.audio_features, aesthetic, tags=tags)
        combined.append((text_s + audio_lambda * a, track))
    combined.sort(key=lambda kv: -kv[0])
    return combined


def recommend_tracks(
    payload,
    *,
    top_k: int = 20,
    results_per_query: int = DEFAULT_RESULTS_PER_QUERY,
    audio_pool_size: int = DEFAULT_AUDIO_POOL_SIZE,
    encoder: FashionBertEncoder | None = None,
    catalog: LocalCatalogClient | None = None,
    reddit_index: RedditTextIndex | None = None,
    use_query_expansion: bool = True,
    market: str | None = None,
    queries: Iterable[str] | None = None,
    image_tags: Iterable[ExtractedTag] | None = None,
    audio_lambda: float = DEFAULT_AUDIO_LAMBDA,
) -> list[dict[str, Any]]:
    """Generate a playlist of real Spotify tracks matching the vibe payload.

    Args:
        payload: Vision payload from ``analyze_images``. Used to build search
            queries and the re-ranking query.
        top_k: Number of tracks to return.
        results_per_query: Per-query candidate pool size from the catalog.
            Higher widens the pool the re-rankers see.
        encoder: Optional fashion-bert encoder. Falls back to a process-wide
            singleton if omitted.
        catalog: Optional catalog client. Falls back to the process-wide
            local catalog (``vibecheck.rec.local_catalog``). Any object with
            a ``search_tracks(query, *, limit, market)`` method that returns
            Spotify-shaped dicts works -- this is how tests inject stubs and
            how live-Spotify calls can still be plugged in.
        reddit_index: Optional Reddit FAISS index. When provided, the
            re-ranking query is expanded the same way as item retrieval.
        use_query_expansion: Toggle for the above. Defaults to True.
        market: Optional ISO-3166-1 market code (ignored by the local catalog).
        queries: Optional override; if passed, we skip ``build_search_queries``.
        image_tags: Optional structured tags extracted from the source image.
            Used to nudge the audio profile (see
            ``vibecheck.rec.spotify_audio.VISUAL_TAG_NUDGES``). When omitted,
            the unmodified base profile is used.
        audio_lambda: Weight on the audio similarity in the combined re-rank.
            Set to ``0.0`` to disable the audio re-rank (text-only ablation).

    Returns:
        A list of track dicts (see ``Track.to_dict``) ordered by descending
        combined text + audio similarity to the vibe. Empty list on any
        failure -- the caller (pipeline) wraps this in a try/except and
        degrades gracefully.
    """
    search_queries = list(queries) if queries is not None else build_search_queries(payload)
    catalog = catalog or get_default_local_client()
    top_aesthetic = _top_aesthetic(payload)

    # If neither candidate generator can produce anything (empty payload + no
    # recognised aesthetic), short-circuit so we don't load the catalog for
    # no reason.
    if not search_queries and not top_aesthetic:
        return []

    seen: dict[str, Track] = {}

    # 1. Keyword search: cheap, narrow, and hit-or-miss against the catalog.
    #    Aesthetic vocab terms (e.g. "dark academia") often return zero rows;
    #    generic terms (e.g. "warm") return many. We take what we can get.
    for query in search_queries:
        try:
            raw_items = catalog.search_tracks(
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

    # 2. Audio-feature filter: backfills the candidate pool with tracks that
    #    acoustically match the predicted aesthetic, so the playlist still
    #    has material to re-rank when keyword search misses. This is what
    #    makes the swap from Spotify's learned search to a literal catalog
    #    actually work.
    if top_aesthetic and audio_pool_size > 0 and hasattr(catalog, "search_by_aesthetic"):
        try:
            audio_pool = catalog.search_by_aesthetic(
                top_aesthetic,
                limit=audio_pool_size,
                image_tags=image_tags,
            )
        except Exception:  # noqa: BLE001 - keep the pipeline alive on filter bugs
            audio_pool = []
        for raw in audio_pool:
            track = normalize_track(raw)
            if track and track.spotify_id not in seen:
                seen[track.spotify_id] = track

    if not seen:
        return []

    encoder = encoder or _shared_encoder()
    text_ranked = _rerank_with_encoder(
        list(seen.values()),
        payload,
        encoder=encoder,
        reddit_index=reddit_index,
        use_query_expansion=use_query_expansion,
    )

    ranked = _combine_text_and_audio(
        text_ranked,
        aesthetic=top_aesthetic,
        image_tags=image_tags,
        audio_lambda=audio_lambda,
    )

    # Second dedupe pass: the catalog often has multiple IDs for what
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

    results = [track.to_dict(score=score) for score, track in deduped[:top_k]]

    # The local catalog has no album art. Enrich the final top-K with one
    # /v1/tracks batch call (~200ms, no rate limit for 10 IDs). Silently
    # no-ops if Spotify credentials are missing or the network is down --
    # tracks then render with the music-note placeholder in the UI.
    try:
        from vibecheck.rec.spotify_client import enrich_album_art

        enrich_album_art(results)
    except Exception:
        pass

    return results


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
