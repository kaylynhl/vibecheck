"""Thin wrapper around the fine-tuned fashion-bert sentence transformer."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL_PATH = REPO_ROOT / "reddit" / "fashion-bert-output-v2"


class FashionBertEncoder:
    """Lazy-loaded sentence-transformer that returns L2-normalized vectors.

    The actual ``sentence_transformers`` import is deferred until the first
    ``encode`` call so that importing this module is cheap (no torch load).
    """

    def __init__(self, model_path: Path | str | None = None) -> None:
        self._model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self._model = None

    @property
    def model(self):
        """Return the underlying SentenceTransformer, loading it on demand."""
        if self._model is None:
            if not self._model_path.exists():
                raise FileNotFoundError(
                    f"fashion-bert model not found at {self._model_path}. "
                    "Make sure reddit/fashion-bert-output-v2/ is in the repo."
                )
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(str(self._model_path))
        return self._model

    @property
    def dim(self) -> int:
        """Dimensionality of output embeddings (384 for v2 / MiniLM)."""
        return self.model.get_sentence_embedding_dimension()

    def encode(
        self,
        texts: Sequence[str],
        *,
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> np.ndarray:
        """Encode a list of strings into an (N, dim) L2-normalized float32 matrix."""
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        embeddings = self.model.encode(
            list(texts),
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=show_progress,
        ).astype(np.float32)
        return l2_normalize(embeddings)


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    """Row-normalize so dot product equals cosine similarity."""
    if matrix.size == 0:
        return matrix
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.clip(norms, 1e-8, None)
