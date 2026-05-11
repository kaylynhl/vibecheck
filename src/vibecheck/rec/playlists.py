"""Vibe-to-playlist recommendation via fashion-bert title embeddings.

We encode each playlist *title* with the same fashion-bert model that powers
item retrieval and run a FAISS nearest-neighbor search at query time. The
fashion-tuned encoder is not music-domain, so this is a deliberate
substitution; see PLAN.md Step 5 for the rationale and the upgrade path
(fine-tune a music-bert on hand-curated (vibe, title) pairs if results are
bad).

Loader resolution order, similar to ``rec.products``:

1. Cached embeddings at ``data/processed/playlist_embeddings.npy``.
2. ``data/raw/spotify_playlists.csv`` -- the Kaggle dataset
   (https://www.kaggle.com/datasets/andrewmvd/spotify-playlists). Needs at
   least a ``name`` or ``title`` column.
3. ``data/seed/playlist_seeds.json`` -- a bundled fallback set so the
   pipeline works without any external download.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from vibecheck.rec.encoder import FashionBertEncoder, l2_normalize


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_PATH = REPO_ROOT / "data" / "processed" / "playlist_embeddings.npy"
DEFAULT_SEED_PATH = REPO_ROOT / "data" / "seed" / "playlist_seeds.json"
DEFAULT_RAW_CSV = REPO_ROOT / "data" / "raw" / "spotify_playlists.csv"


@dataclass
class Playlist:
    """A single playlist entry (title-only; we don't fetch tracks here)."""

    title: str
    aesthetic: str | None = None
    curator: str | None = None
    url: str | None = None

    def encode_text(self) -> str:
        """Text used to compute this playlist's embedding (title only)."""
        return self.title.strip()

    def to_dict(self, score: float | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {"title": self.title}
        if self.aesthetic:
            out["aesthetic"] = self.aesthetic
        if self.curator:
            out["curator"] = self.curator
        if self.url:
            out["url"] = self.url
        if score is not None:
            out["score"] = round(float(score), 4)
        return out


@dataclass
class PlaylistIndex:
    """In-memory FAISS index over playlist title embeddings."""

    playlists: list[Playlist]
    embeddings: np.ndarray
    _index: Any = field(default=None, init=False, repr=False)

    @property
    def index(self):
        if self._index is None:
            import faiss

            self._index = faiss.IndexFlatIP(self.embeddings.shape[1])
            self._index.add(self.embeddings)
        return self._index

    def search(self, query_vec: np.ndarray, k: int = 5) -> list[tuple[float, Playlist]]:
        """Return (score, playlist) pairs for the k most similar playlist titles."""
        if query_vec.ndim == 1:
            query_vec = query_vec[None, :]
        if k <= 0 or not self.playlists:
            return []
        scores, idxs = self.index.search(query_vec.astype(np.float32), k)
        results: list[tuple[float, Playlist]] = []
        for score, idx in zip(scores[0], idxs[0]):
            if 0 <= idx < len(self.playlists):
                results.append((float(score), self.playlists[idx]))
        return results


def load_playlists_from_seed(path: Path = DEFAULT_SEED_PATH) -> list[Playlist]:
    """Load the bundled fallback seed set."""
    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return [
        Playlist(
            title=row["title"],
            aesthetic=row.get("aesthetic"),
            curator=row.get("curator"),
            url=row.get("url"),
        )
        for row in raw
        if row.get("title")
    ]


def load_playlists_from_csv(path: Path) -> list[Playlist]:
    """Load playlists from a generic CSV.

    Accepts any of ``name`` / ``title`` / ``playlist_name`` for the title
    column and tries common synonyms for curator and URL.
    """
    with path.open("r", encoding="utf-8", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample)
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(fh, dialect=dialect)
        if reader.fieldnames is None:
            return []
        fieldnames = [name.lower() for name in reader.fieldnames]

        def pick(candidates: tuple[str, ...]) -> str | None:
            for cand in candidates:
                if cand in fieldnames:
                    return reader.fieldnames[fieldnames.index(cand)]
            return None

        title_col = pick(("title", "name", "playlist_name", "playlistname"))
        curator_col = pick(("curator", "owner", "user", "user_id"))
        url_col = pick(("url", "link", "spotify_url"))
        if title_col is None:
            return []

        out: list[Playlist] = []
        seen: set[str] = set()
        for row in reader:
            title = (row.get(title_col) or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            out.append(
                Playlist(
                    title=title,
                    curator=(row.get(curator_col).strip() if curator_col and row.get(curator_col) else None),
                    url=(row.get(url_col).strip() if url_col and row.get(url_col) else None),
                )
            )
        return out


def load_playlist_index(
    *,
    encoder: FashionBertEncoder | None = None,
    source_csv: Path | str | None = None,
    seed_path: Path | str = DEFAULT_SEED_PATH,
    cache_path: Path | str | None = DEFAULT_CACHE_PATH,
    rebuild: bool = False,
) -> PlaylistIndex:
    """Build (or load) the playlist index.

    Resolution order: cached embeddings -> source CSV -> bundled seeds.
    Embeddings are always L2-normalized so cosine similarity = dot product.
    """
    seed_path = Path(seed_path)
    cache_path = Path(cache_path) if cache_path else None
    source_csv = Path(source_csv) if source_csv else None
    if source_csv is None and DEFAULT_RAW_CSV.exists():
        source_csv = DEFAULT_RAW_CSV

    if source_csv and source_csv.exists():
        playlists = load_playlists_from_csv(source_csv)
        if not playlists:
            playlists = load_playlists_from_seed(seed_path)
    else:
        playlists = load_playlists_from_seed(seed_path)

    if not playlists:
        raise FileNotFoundError(
            "No playlists available: source CSV missing and seed file empty."
        )

    embeddings: np.ndarray | None = None
    if cache_path and cache_path.exists() and not rebuild:
        cached = np.load(cache_path)
        if cached.shape[0] == len(playlists):
            embeddings = cached.astype(np.float32)

    if embeddings is None:
        encoder = encoder or FashionBertEncoder()
        embeddings = encoder.encode(
            [p.encode_text() for p in playlists], show_progress=True
        )
        if cache_path is not None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            np.save(cache_path, embeddings)

    embeddings = l2_normalize(embeddings)
    return PlaylistIndex(playlists=playlists, embeddings=embeddings)


def recommend_playlist(
    payload,
    *,
    top_k: int = 5,
    encoder: FashionBertEncoder | None = None,
    playlist_index: PlaylistIndex | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    """Return up to ``top_k`` playlist matches for a vision payload (or raw query)."""
    if query is None:
        from vibecheck.rec.recommend import build_query_string

        query = build_query_string(payload)
    if not query:
        return []

    encoder = encoder or FashionBertEncoder()
    playlist_index = playlist_index or load_playlist_index(encoder=encoder)

    vec = encoder.encode([query])
    results = playlist_index.search(vec, k=top_k)
    return [p.to_dict(score=score) for score, p in results]
