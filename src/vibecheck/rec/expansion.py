"""Reddit-corpus query expansion to enrich short vibe queries with real vocabulary."""

from __future__ import annotations

import numpy as np

from vibecheck.rec.encoder import l2_normalize
from vibecheck.rec.text_index import RedditTextIndex


def expand_query(
    query_vec: np.ndarray,
    reddit_index: RedditTextIndex,
    *,
    k_corpus: int = 10,
    alpha: float = 1.0,
    beta: float = 0.75,
) -> np.ndarray:
    """Blend a query embedding with the mean of its top-k Reddit neighbors.

    Implements the formula from the prototype notebook::

        expanded = alpha * query + beta * mean(top_k Reddit utterance embeddings)

    Setting ``beta=0`` recovers the un-expanded query.
    """
    if query_vec.ndim == 1:
        query_vec = query_vec[None, :]

    if k_corpus <= 0 or beta == 0.0:
        return l2_normalize(alpha * query_vec)

    neighbor_embs = reddit_index.top_k_embeddings(query_vec, k=k_corpus)
    if neighbor_embs.shape[0] == 0:
        return l2_normalize(alpha * query_vec)

    blended = alpha * query_vec + beta * neighbor_embs.mean(axis=0, keepdims=True)
    return l2_normalize(blended)
