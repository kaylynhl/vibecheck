"""Tests for the caption-similarity vibe fallback (`vibe.embedding_match`).

The fallback fires whenever the primary tag-based scorer can't find any
signal in the extracted tags (top vibe score < 0.05). Without this layer,
unusual scenes -- restaurants, niche aesthetics, non-Western interiors --
produce a degenerate "everything at 2 %" UI. With it, the pipeline can
still surface a meaningful top vibe by comparing the vision model's
free-text description against per-vibe embedding signatures.

We mock the encoder so this test never touches sentence-transformers
(saves ~3 s of CI time per run).
"""

from __future__ import annotations

import numpy as np
import pytest

from vibecheck.vibe import embedding_match


class _FakeEncoder:
    """Returns deterministic L2-normalised vectors based on a hash of the text."""

    def encode(self, texts):
        out = np.zeros((len(texts), 4), dtype=np.float32)
        for i, t in enumerate(texts):
            # Synthesize a deterministic vector that aligns with one of three
            # "vibe" axes depending on the keywords present.
            if "minimalist" in t.lower() or "clean lines" in t.lower():
                out[i] = [1.0, 0.0, 0.0, 0.0]
            elif "grunge" in t.lower() or "distressed" in t.lower():
                out[i] = [0.0, 1.0, 0.0, 0.0]
            elif "boho" in t.lower() or "macrame" in t.lower():
                out[i] = [0.0, 0.0, 1.0, 0.0]
            else:
                # Otherwise lean slightly towards minimalist (the "modern"
                # category most general descriptions match).
                out[i] = [0.7, 0.1, 0.1, 0.7]
                out[i] /= np.linalg.norm(out[i])
        return out


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch: pytest.MonkeyPatch):
    """Each test gets a fresh module-level cache + a fake encoder/matrix."""
    embedding_match.reset_state()

    fake_encoder = _FakeEncoder()
    # Three fake vibes that map to the three orthogonal axes.
    fake_matrix = np.array(
        [
            [1.0, 0.0, 0.0, 0.0],  # minimalist
            [0.0, 1.0, 0.0, 0.0],  # grunge
            [0.0, 0.0, 1.0, 0.0],  # boho
        ],
        dtype=np.float32,
    )
    fake_names = ("minimalist", "grunge", "boho")
    monkeypatch.setattr(
        embedding_match,
        "_load_state",
        lambda: (fake_encoder, fake_matrix, fake_names),
    )
    yield
    embedding_match.reset_state()


def test_returns_empty_for_blank_caption() -> None:
    scores, notes = embedding_match.score_vibes_by_caption("")
    assert scores == []
    assert any("no visual summary" in n.lower() for n in notes)


def test_top_match_aligns_with_keyword_in_caption() -> None:
    scores, notes = embedding_match.score_vibes_by_caption(
        "A clean-lines minimalist room with restrained palette."
    )
    assert scores[0].vibe == "minimalist"
    assert scores[0].score == pytest.approx(1.0, abs=1e-3)
    assert scores[1].score < scores[0].score
    assert any("Caption-similarity" in n for n in notes)


def test_returns_full_ranking_in_descending_order() -> None:
    scores, _ = embedding_match.score_vibes_by_caption(
        "A grunge distressed darkroom with film grain."
    )
    assert [s.vibe for s in scores] == ["grunge", "minimalist", "boho"] or \
           [s.vibe for s in scores][0] == "grunge"
    assert all(scores[i].score >= scores[i + 1].score for i in range(len(scores) - 1))


def test_top_k_slices_ranking() -> None:
    scores, _ = embedding_match.score_vibes_by_caption(
        "minimalist clean room", top_k=2
    )
    assert len(scores) == 2
