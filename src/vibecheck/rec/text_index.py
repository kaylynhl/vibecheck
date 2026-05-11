"""FAISS index over filtered Reddit utterances, used for query expansion."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from vibecheck.rec.encoder import FashionBertEncoder, l2_normalize

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CORPUS_PATH = REPO_ROOT / "reddit" / "filtered_reddit_texts.csv"
DEFAULT_CACHE_PATH = REPO_ROOT / "data" / "processed" / "reddit_embeddings.npy"


@dataclass
class RedditTextIndex:
    """In-memory FAISS index over Reddit utterance embeddings."""

    texts: list[str]
    embeddings: np.ndarray
    _index: Any = field(default=None, init=False, repr=False)

    @property
    def index(self):
        """Return the lazily-built FAISS IndexFlatIP."""
        if self._index is None:
            import faiss

            self._index = faiss.IndexFlatIP(self.embeddings.shape[1])
            self._index.add(self.embeddings)
        return self._index

    def top_k_embeddings(self, query_vec: np.ndarray, k: int = 10) -> np.ndarray:
        """Return embeddings of the k nearest Reddit utterances to ``query_vec``."""
        if query_vec.ndim == 1:
            query_vec = query_vec[None, :]
        if k <= 0 or len(self.texts) == 0:
            return np.zeros((0, self.embeddings.shape[1]), dtype=np.float32)
        _, idxs = self.index.search(query_vec.astype(np.float32), k)
        return self.embeddings[idxs[0]]

    def top_k_texts(self, query_vec: np.ndarray, k: int = 10) -> list[tuple[float, str]]:
        """Return (score, text) pairs for the k nearest Reddit utterances."""
        if query_vec.ndim == 1:
            query_vec = query_vec[None, :]
        if k <= 0 or len(self.texts) == 0:
            return []
        scores, idxs = self.index.search(query_vec.astype(np.float32), k)
        out: list[tuple[float, str]] = []
        for score, idx in zip(scores[0], idxs[0]):
            if 0 <= idx < len(self.texts):
                out.append((float(score), self.texts[idx]))
        return out


def load_reddit_index(
    *,
    encoder: FashionBertEncoder | None = None,
    corpus_path: Path | str = DEFAULT_CORPUS_PATH,
    cache_path: Path | str | None = DEFAULT_CACHE_PATH,
    rebuild: bool = False,
) -> RedditTextIndex:
    """Load (or build + cache) the Reddit-utterance FAISS index.

    On first run this encodes ~62k Reddit posts and caches the result to
    ``data/processed/reddit_embeddings.npy``. Subsequent runs reuse the cache.
    """
    corpus_path = Path(corpus_path)
    cache_path = Path(cache_path) if cache_path else None

    texts = _read_text_corpus(corpus_path)
    if not texts:
        raise FileNotFoundError(
            f"No Reddit utterances found at {corpus_path}. "
            "Make sure reddit/filtered_reddit_texts.csv is in the repo."
        )

    embeddings: np.ndarray | None = None
    if cache_path and cache_path.exists() and not rebuild:
        cached = np.load(cache_path)
        if cached.shape[0] == len(texts):
            embeddings = cached.astype(np.float32)

    if embeddings is None:
        encoder = encoder or FashionBertEncoder()
        embeddings = encoder.encode(texts, show_progress=True)
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            np.save(cache_path, embeddings)

    embeddings = l2_normalize(embeddings)
    return RedditTextIndex(texts=texts, embeddings=embeddings)


def _read_text_corpus(path: Path) -> list[str]:
    """Read the Reddit text corpus, one utterance per CSV row."""
    if not path.exists():
        return []
    texts: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row:
                continue
            text = (row[0] or "").strip()
            if text:
                texts.append(text)
    return texts
