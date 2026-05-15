"""Local Spotify-style catalog client backed by a static CSV.

Replaces the live Spotify ``/v1/search`` call in the playlist recommender
with a pandas lookup over a 1.16M-track Kaggle catalog. Spotify's
``/v1/recommendations`` is deprecated for new apps as of Nov 27 2024 and
``/v1/search`` clamps ``limit`` to 10 on Client Credentials tokens (silent
HTTP 400 for higher values), which makes it a poor backbone for a real
recommender. A static CSV side-steps both problems and makes the system
fully reproducible -- no API credentials needed to run the pipeline.

The returned dicts follow the same shape as Spotify's track JSON so that
``vibecheck.rec.playlists.normalize_track`` can consume them unchanged.
The two visual fields Spotify provides (album cover image, preview URL)
are absent from the catalog and surface as ``None``; the mobile UI is
already prepared for both being missing.

Audio features (danceability, energy, valence, ...) are attached under a
non-Spotify ``audio_features`` key on each track dict so the downstream
re-ranker can use them without a second pass over the CSV.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from vibecheck.rec.spotify_audio import (
    apply_visual_tag_nudges,
    get_profile,
    _normalise_feature,
)
from vibecheck.schemas import ExtractedTag


# Columns we keep from the Kaggle dataset. Anything not listed here is
# discarded after load to keep the in-memory frame small. The dropped
# columns (``duration_ms``, ``time_signature``, the unnamed index column)
# are present in the CSV but not used by our pipeline.
_METADATA_COLS = ("track_id", "track_name", "artist_name", "popularity", "year", "genre")
_AUDIO_FEATURE_COLS = (
    "danceability",
    "energy",
    "key",
    "loudness",
    "mode",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
)
_KEPT_COLS = _METADATA_COLS + _AUDIO_FEATURE_COLS

# Default location for the Kaggle CSV. Gitignored due to size (168 MB).
# Override per-instance for tests.
DEFAULT_CSV_PATH = (
    Path(__file__).resolve().parents[3] / "spotify" / "spotify_data.csv"
)


class LocalCatalogClient:
    """Drop-in replacement for ``SpotifyClient`` backed by a CSV.

    The interface mirrors ``SpotifyClient.search_tracks`` so the playlist
    recommender does not need to know which one it is talking to.
    Construction is cheap: the CSV is loaded lazily on the first search.
    """

    def __init__(
        self,
        csv_path: Path | str | None = None,
        *,
        max_pool_per_query: int = 50,
    ) -> None:
        self._csv_path = Path(csv_path) if csv_path else DEFAULT_CSV_PATH
        self._df: pd.DataFrame | None = None
        self._lock = threading.Lock()
        self._max_pool_per_query = max_pool_per_query

    # ---- loading ----------------------------------------------------------

    def _load(self) -> pd.DataFrame:
        if self._df is not None:
            return self._df
        with self._lock:
            if self._df is not None:  # second check after acquiring lock
                return self._df
            if not self._csv_path.exists():
                raise FileNotFoundError(
                    f"Spotify catalog CSV not found at {self._csv_path}. "
                    "Place the Kaggle dataset at that path "
                    "(see scripts/download_spotify_catalog.py) and retry."
                )
            df = pd.read_csv(self._csv_path)
            df.columns = [c.strip().lower() for c in df.columns]
            usable = [c for c in _KEPT_COLS if c in df.columns]
            df = df[usable].copy()
            for col in ("track_name", "artist_name", "genre"):
                if col in df.columns:
                    df[col] = df[col].fillna("").astype(str)
            # Pre-compute a lower-cased haystack column once so per-query
            # matching is a single ``str.contains`` instead of three.
            df["_search"] = (
                df.get("track_name", "")
                + " "
                + df.get("artist_name", "")
                + " "
                + df.get("genre", "")
            ).str.lower()
            self._df = df
            return self._df

    # ---- search -----------------------------------------------------------

    def search_tracks(
        self,
        query: str,
        *,
        limit: int = 50,
        market: str | None = None,  # noqa: ARG002 - kept for interface parity
        max_retries: int = 3,       # noqa: ARG002 - kept for interface parity
    ) -> list[dict[str, Any]]:
        """Return up to ``limit`` tracks matching ``query``.

        Matching is case-insensitive substring search across the combined
        title + artist + genre column, sorted by Spotify popularity desc.
        ``market`` and ``max_retries`` are accepted to mirror ``SpotifyClient``
        but ignored -- there is no rate limit or regional catalog here.
        """
        if not query or not query.strip():
            return []
        df = self._load()
        needle = query.strip().lower()
        # Escape regex metacharacters so queries with punctuation behave like
        # literal substring matches.
        mask = df["_search"].str.contains(needle, regex=False, na=False)
        if not mask.any():
            return []
        matches = df.loc[mask]
        ranked = matches.nlargest(
            min(limit, self._max_pool_per_query),
            "popularity",
        )
        return [_row_to_spotify_dict(row) for _, row in ranked.iterrows()]

    # ---- audio-feature filter --------------------------------------------

    def search_by_aesthetic(
        self,
        aesthetic: str,
        *,
        limit: int = 200,
        image_tags: Iterable[ExtractedTag] | None = None,
        popularity_floor: int = 30,
    ) -> list[dict[str, Any]]:
        """Return the top ``limit`` tracks by audio similarity to an aesthetic.

        Aesthetic labels like "dark academia" do not appear in track titles,
        artist names, or Spotify's coarse genre field, so substring search
        alone is a poor candidate generator -- a "dark academia" query against
        the Kaggle catalog finds zero matches. This method side-steps that by
        scoring every track in the catalog against the aesthetic's audio
        profile (see :mod:`vibecheck.rec.spotify_audio`) and returning the
        best matches. It is used as a *complement* to keyword search inside
        ``recommend_tracks`` so the playlist still has material to re-rank
        even when none of the keyword queries hit the catalog.

        Args:
            aesthetic: Aesthetic name (will be normalised via ``get_profile``).
            limit: Maximum number of tracks to return after sorting.
            image_tags: Optional ExtractedTag list; passed through to
                ``apply_visual_tag_nudges`` so the same aesthetic yields
                photo-specific orderings.
            popularity_floor: Drop tracks with popularity below this threshold
                before scoring, to avoid pulling obscure recordings to the top
                just because their features happen to match. Default 30 (the
                catalog's median is ~30-40).
        """
        profile = get_profile(aesthetic)
        if profile is None:
            return []
        if image_tags is not None:
            profile = apply_visual_tag_nudges(profile, image_tags)

        df = self._load()
        if "popularity" in df.columns and popularity_floor > 0:
            pool = df[df["popularity"] >= popularity_floor]
        else:
            pool = df
        if pool.empty:
            return []

        # Vectorised scoring: 1 - weighted_mean(|track_f - target_f|) where
        # both sides are pre-normalised. Equivalent to spotify_audio.audio_score
        # but operates on the full DataFrame at once -- ~50 ms over 1.16M rows.
        used_weight = 0.0
        weighted_distance = np.zeros(len(pool), dtype=np.float32)
        for feature, (target, weight) in profile.items():
            if feature not in pool.columns:
                continue
            norm_target = _normalise_feature(feature, target)
            observed = pool[feature].to_numpy(dtype=np.float32, copy=False)
            if feature in {"tempo", "loudness"}:
                # Apply the same bounds-based normalisation we use scalarly.
                observed = np.vectorize(
                    lambda v, f=feature: _normalise_feature(f, float(v))
                )(observed).astype(np.float32)
            else:
                observed = np.clip(observed, 0.0, 1.0)
            weighted_distance += weight * np.abs(norm_target - observed)
            used_weight += weight
        if used_weight <= 0:
            return []
        scores = 1.0 - (weighted_distance / used_weight)

        # argpartition + sort is much faster than a full sort over 1M rows.
        k = int(min(limit, len(pool)))
        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(-scores[top_idx])]
        top_rows = pool.iloc[top_idx]
        return [_row_to_spotify_dict(row) for _, row in top_rows.iterrows()]


# ---- module-level singleton ----------------------------------------------

_DEFAULT_CLIENT: LocalCatalogClient | None = None
_DEFAULT_CLIENT_LOCK = threading.Lock()


def get_default_local_client() -> LocalCatalogClient:
    """Process-wide singleton local catalog client."""
    global _DEFAULT_CLIENT
    with _DEFAULT_CLIENT_LOCK:
        if _DEFAULT_CLIENT is None:
            _DEFAULT_CLIENT = LocalCatalogClient()
        return _DEFAULT_CLIENT


def reset_default_local_client() -> None:
    """Drop the cached singleton. Useful in tests after monkey-patching."""
    global _DEFAULT_CLIENT
    with _DEFAULT_CLIENT_LOCK:
        _DEFAULT_CLIENT = None


# ---- row -> Spotify track dict -------------------------------------------


def _row_to_spotify_dict(row: pd.Series) -> dict[str, Any]:
    """Translate a catalog row into the same shape as Spotify's track JSON."""
    track_id = str(row.get("track_id", "")) or ""
    audio_features: dict[str, float] = {}
    for col in _AUDIO_FEATURE_COLS:
        if col in row and pd.notna(row[col]):
            audio_features[col] = float(row[col])

    return {
        "id": track_id,
        "name": str(row.get("track_name", "")),
        "artists": _split_artists(str(row.get("artist_name", ""))),
        "album": {
            "name": "",     # not in catalog
            "images": [],   # not in catalog (mobile UI handles this)
        },
        "preview_url": None,  # not in catalog (Spotify rarely returns this anyway)
        "external_urls": {
            "spotify": f"https://open.spotify.com/track/{track_id}" if track_id else "",
        },
        "duration_ms": None,
        "audio_features": audio_features,
        "popularity": int(row["popularity"]) if pd.notna(row.get("popularity")) else None,
        "genre": str(row.get("genre", "")),
    }


def _split_artists(raw: str) -> list[dict[str, str]]:
    """Catalog stores artists as a free-form string; split on commas + ' & '.

    Returns a list of ``{"name": ...}`` dicts so the result still parses
    through ``vibecheck.rec.playlists.normalize_track`` without changes.
    """
    if not raw:
        return []
    # Replace ' & ' with ',' so a single split rule covers both separators.
    flat = raw.replace(" & ", ",").replace(" and ", ",")
    names: Iterable[str] = (s.strip() for s in flat.split(","))
    return [{"name": n} for n in names if n]
