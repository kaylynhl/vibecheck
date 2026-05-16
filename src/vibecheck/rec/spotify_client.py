"""Minimal Spotify Web API client used by the playlist recommender.

We only need the Client Credentials Flow (server-to-server, no user OAuth)
because all the catalog endpoints we hit are public read-only metadata.
Tokens are cached in-process for ~55 minutes (real expiry is 60 minutes;
we refresh slightly early to avoid a race) and auto-refreshed on 401.

The recommender is designed to call this client from a long-running
backend process (e.g. the FastAPI server in Step 8), so the in-process
cache is the right place to keep the token. If we ever go serverless,
swap this for a Redis-backed cache.
"""

from __future__ import annotations

import base64
import os
import threading
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import requests

from vibecheck.errors import ConfigurationError, VibecheckError


SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

# Refresh slightly before the real expiry to give in-flight requests a chance
# to complete without racing the refresh.
TOKEN_SAFETY_MARGIN_SECONDS = 60

# /v1/search rejects limit > 10 with HTTP 400 "Invalid limit" for new
# Client Credentials apps (undocumented). We clamp to 10 to avoid silently
# returning empty results.
SPOTIFY_SEARCH_MAX_LIMIT = 10


class SpotifyAPIError(VibecheckError):
    """Raised when the Spotify Web API returns an unrecoverable error."""


@dataclass
class _CachedToken:
    access_token: str
    expires_at: float


@dataclass
class SpotifyClient:
    """Thread-safe, token-caching Spotify Web API client.

    Credentials are read from ``SPOTIFY_CLIENT_ID`` / ``SPOTIFY_CLIENT_SECRET``
    on first use unless they are passed in explicitly. We do not eagerly
    refresh -- the first call to ``search_tracks`` triggers token retrieval.
    """

    client_id: str | None = None
    client_secret: str | None = None
    timeout: float = 15.0
    _token: _CachedToken | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _session: requests.Session | None = field(default=None, init=False, repr=False)

    def _ensure_credentials(self) -> tuple[str, str]:
        cid = self.client_id or os.environ.get("SPOTIFY_CLIENT_ID")
        secret = self.client_secret or os.environ.get("SPOTIFY_CLIENT_SECRET")
        if not cid or not secret:
            raise ConfigurationError(
                "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set "
                "(in env or .env) to call the Spotify Web API."
            )
        return cid, secret

    def _session_get(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _fetch_token(self) -> _CachedToken:
        """Exchange client credentials for an access token (Client Credentials Flow)."""
        cid, secret = self._ensure_credentials()
        creds = base64.b64encode(f"{cid}:{secret}".encode()).decode()
        response = self._session_get().post(
            SPOTIFY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise SpotifyAPIError(
                f"Spotify token request failed: {response.status_code} {response.text[:200]}"
            )
        payload = response.json()
        return _CachedToken(
            access_token=payload["access_token"],
            expires_at=time.time() + float(payload.get("expires_in", 3600)) - TOKEN_SAFETY_MARGIN_SECONDS,
        )

    def _get_token(self, force_refresh: bool = False) -> str:
        with self._lock:
            if (
                force_refresh
                or self._token is None
                or self._token.expires_at <= time.time()
            ):
                self._token = self._fetch_token()
            return self._token.access_token

    def get_tracks(
        self,
        ids: list[str],
        *,
        market: str | None = None,
        max_retries: int = 3,
        warn_on_error: bool = True,
    ) -> list[dict[str, Any]]:
        """Fetch metadata for up to 50 track IDs in a single /v1/tracks call.

        Used to enrich tracks pulled from the local Kaggle catalog with the
        one field the catalog lacks: album art. Returns the raw Spotify
        track objects in the same order as ``ids``; missing IDs return
        ``None`` per Spotify's contract, which we filter out.
        """
        ids = [i for i in ids if i]
        if not ids:
            return []
        # /v1/tracks?ids=... caps at 50 per call. Split if the caller went over.
        if len(ids) > 50:
            collected: list[dict[str, Any]] = []
            for i in range(0, len(ids), 50):
                collected.extend(
                    self.get_tracks(
                        ids[i : i + 50],
                        market=market,
                        max_retries=max_retries,
                        warn_on_error=warn_on_error,
                    )
                )
            return collected

        params: dict[str, Any] = {"ids": ",".join(ids)}
        if market:
            params["market"] = market

        url = f"{SPOTIFY_API_BASE}/tracks"
        session = self._session_get()

        for attempt in range(max_retries):
            token = self._get_token()
            response = session.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=self.timeout,
            )
            if response.status_code == 200:
                tracks = response.json().get("tracks", []) or []
                return [t for t in tracks if t]
            if response.status_code == 401:
                self._get_token(force_refresh=True)
                continue
            if response.status_code == 429:
                wait = max(1, int(response.headers.get("Retry-After", "1") or "1"))
                time.sleep(min(wait, 30))
                continue
            if warn_on_error:
                import sys as _sys

                print(
                    f"[spotify] /tracks {response.status_code} for {len(ids)} ids: "
                    f"{response.text[:150]}",
                    file=_sys.stderr,
                )
            return []
        return []

    def search_tracks(
        self,
        query: str,
        *,
        limit: int = SPOTIFY_SEARCH_MAX_LIMIT,
        market: str | None = None,
        max_retries: int = 3,
        warn_on_error: bool = True,
    ) -> list[dict[str, Any]]:
        """Hit /v1/search?type=track for one query and return raw track items.

        Handles 429 (Retry-After) and 401 (one auto-refresh + retry). On any
        other non-200 response we print a single warning line to stderr (so
        debugging is not a silent black hole) and return an empty list.
        """
        if not query.strip():
            return []
        params: dict[str, Any] = {
            "q": query,
            "type": "track",
            "limit": min(limit, SPOTIFY_SEARCH_MAX_LIMIT),
        }
        if market:
            params["market"] = market

        url = f"{SPOTIFY_API_BASE}/search"
        session = self._session_get()

        for attempt in range(max_retries):
            token = self._get_token()
            response = session.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=self.timeout,
            )
            if response.status_code == 200:
                data = response.json().get("tracks", {})
                return [t for t in data.get("items", []) or [] if t]
            if response.status_code == 401:
                # Token went stale earlier than expected; force a refresh once.
                self._get_token(force_refresh=True)
                continue
            if response.status_code == 429:
                wait = max(1, int(response.headers.get("Retry-After", "1") or "1"))
                time.sleep(min(wait, 30))
                continue
            if warn_on_error:
                import sys as _sys

                print(
                    f"[spotify] {response.status_code} for query={query!r}: "
                    f"{response.text[:150]}",
                    file=_sys.stderr,
                )
            return []
        return []


_DEFAULT_CLIENT: SpotifyClient | None = None
_DEFAULT_CLIENT_LOCK = threading.Lock()


def get_default_client() -> SpotifyClient:
    """Process-wide singleton Spotify client used by ``recommend_tracks``."""
    global _DEFAULT_CLIENT
    with _DEFAULT_CLIENT_LOCK:
        if _DEFAULT_CLIENT is None:
            _DEFAULT_CLIENT = SpotifyClient()
        return _DEFAULT_CLIENT


def reset_default_client() -> None:
    """Drop the cached singleton. Only useful for tests."""
    global _DEFAULT_CLIENT
    with _DEFAULT_CLIENT_LOCK:
        _DEFAULT_CLIENT = None


SPOTIFY_OEMBED_URL = "https://open.spotify.com/oembed"


@lru_cache(maxsize=1024)
def _fetch_oembed_thumbnail(track_id: str) -> str | None:
    """Hit Spotify's public oEmbed endpoint and return the 300x300 cover URL.

    oEmbed is auth-free and survives Spotify's November 2024 Client
    Credentials restrictions (which broke /v1/tracks for new dev apps).
    Cached in-process to keep the same playlist regeneration cheap.
    """
    if not track_id:
        return None
    try:
        response = requests.get(
            SPOTIFY_OEMBED_URL,
            params={"url": f"https://open.spotify.com/track/{track_id}"},
            timeout=5.0,
        )
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    try:
        return response.json().get("thumbnail_url")
    except ValueError:
        return None


def enrich_album_art(
    tracks: list[dict[str, Any]],
    *,
    max_workers: int = 8,
) -> None:
    """Populate ``album_image`` on each track via Spotify's public oEmbed.

    Used after ``recommend_tracks`` returns: the local Kaggle catalog has
    every field except album art. oEmbed gives us a 300x300 cover per
    track with one HTTP call (no auth). Calls are parallelised so a
    top-10 playlist enriches in ~500ms instead of ~5s. Mutates ``tracks``
    in place; failures are silent (the UI already handles missing art
    with a music-note placeholder).
    """
    needs_art = [
        t for t in tracks
        if t.get("spotify_id") and not t.get("album_image")
    ]
    if not needs_art:
        return

    from concurrent.futures import ThreadPoolExecutor

    ids = [str(t["spotify_id"]) for t in needs_art]
    with ThreadPoolExecutor(max_workers=min(max_workers, len(ids))) as pool:
        thumbs = list(pool.map(_fetch_oembed_thumbnail, ids))
    for track, thumb in zip(needs_art, thumbs):
        if thumb:
            track["album_image"] = thumb
