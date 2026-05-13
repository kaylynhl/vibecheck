"""Caption-similarity fallback for vibe scoring.

This module provides a semantic fallback: encode the vision model's free
description, encode each vibe's name + description + keyword profile, take
cosine similarity. Returns a ranked list of ``VibeScore`` matches that the
pipeline can use whenever the structured scorer flatlines.

We re-use the existing ``FashionBertEncoder`` (the same model that powers
product retrieval), so no new dependency. Vibe-side embeddings are
computed once per process and cached.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from vibecheck.rec.encoder import FashionBertEncoder
from vibecheck.schemas import VibeScore
from vibecheck.vibe.catalog import VIBE_PROFILES, VibeProfile


def _vibe_corpus(profile: VibeProfile) -> str:
    """Flatten a vibe profile into a single text doc for embedding.

    The keyword phrases carry the actual visual semantics, but the
    description gives the embedding model some natural-language anchor
    so two profiles with overlapping keywords still map to distinct
    points in embedding space.
    """
    keywords = ", ".join(profile.keyword_weights.keys())
    return f"{profile.name}. {profile.description} Visual signals: {keywords}."


_StateTuple = tuple[FashionBertEncoder, np.ndarray, tuple[str, ...]]


@lru_cache(maxsize=1)
def _load_state() -> _StateTuple:
    """Build the vibe embedding matrix on first use.

    Cached for the lifetime of the process -- the vibe catalog is static.
    """
    encoder = FashionBertEncoder()
    profiles = VIBE_PROFILES
    matrix = encoder.encode([_vibe_corpus(p) for p in profiles])
    names = tuple(p.name for p in profiles)
    return encoder, matrix, names


def reset_state() -> None:
    """Drop the cached state. Test-only helper.

    Tolerates the case where ``_load_state`` has been monkeypatched to a
    plain function (without ``cache_clear``).
    """
    cache_clear = getattr(_load_state, "cache_clear", None)
    if cache_clear is not None:
        cache_clear()


def score_vibes_by_caption(
    caption: str,
    *,
    top_k: int | None = None,
) -> tuple[list[VibeScore], list[str]]:
    """Score every vibe in the catalog by cosine similarity to ``caption``.

    Returns
    -------
    scores
        ``VibeScore`` entries for *every* vibe in the catalog (not just the
        top-k), already sorted descending by cosine similarity. Pipeline
        callers slice this for display.
    notes
        Free-form confidence notes (one element) explaining how the score
        was derived. The caller appends these to ``confidence_notes`` so
        the writeup / debug view can tell which scorer produced a result.
    """
    text = (caption or "").strip()
    if not text:
        return [], ["Caption-similarity fallback skipped: no visual summary text available."]

    encoder, matrix, names = _load_state()
    query = encoder.encode([text])  # already L2-normalised
    sims = matrix @ query[0]  # (V,)

    order = np.argsort(-sims)
    if top_k is not None:
        order = order[:top_k]

    scores: list[VibeScore] = []
    for idx in order:
        scores.append(
            VibeScore(
                vibe=names[idx],
                score=float(sims[idx]),
                matched_keywords=[],
                description="",
            )
        )

    top_name = names[int(order[0])]
    top_sim = float(sims[int(order[0])])
    note = (
        f"Caption-similarity fallback used (top match: {top_name} @ "
        f"cosine={top_sim:.3f}). Tag-based scorer had no signal."
    )
    return scores, [note]
