"""Tests for the learned tags->vibe classifier infrastructure.

Training itself is data- and time-dependent, so these tests train a tiny
synthetic model in-memory rather than relying on the joblib produced by
``scripts/train_vibe_classifier.py``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from vibecheck.schemas import ExtractedTag
from vibecheck.vibe.learned import (
    LearnedVibeBundle,
    LearnedVibeError,
    build_feature_index,
    feature_vector,
    load_bundle,
    predict_topk,
    save_bundle,
    score_vibes_learned,
    train_logreg,
)
from vibecheck.vibe.scoring import score_vibes


def test_build_feature_index_is_stable_and_ordered() -> None:
    idx_a = build_feature_index()
    idx_b = build_feature_index()
    assert idx_a == idx_b
    assert all(isinstance(pair, tuple) and len(pair) == 2 for pair in idx_a)
    palette_pairs = [p for p in idx_a if p[0] == "palette"]
    assert palette_pairs == sorted(palette_pairs)


def test_feature_vector_packs_tag_confidences_at_correct_indices() -> None:
    feature_index = build_feature_index()
    tags = [
        ExtractedTag(
            category="palette", value="warm neutrals", confidence=0.9, evidence=""
        ),
        ExtractedTag(category="material", value="leather", confidence=0.7, evidence=""),
    ]

    vec = feature_vector(tags, feature_index)

    assert vec.shape == (len(feature_index),)
    palette_idx = feature_index.index(("palette", "warm neutrals"))
    leather_idx = feature_index.index(("material", "leather"))
    assert vec[palette_idx] == pytest.approx(0.9)
    assert vec[leather_idx] == pytest.approx(0.7)
    assert vec.sum() == pytest.approx(0.9 + 0.7)


def test_feature_vector_dedupes_to_max_confidence() -> None:
    feature_index = build_feature_index()
    tags = [
        ExtractedTag(
            category="palette", value="warm neutrals", confidence=0.5, evidence=""
        ),
        ExtractedTag(
            category="palette", value="warm neutrals", confidence=0.9, evidence=""
        ),
    ]

    vec = feature_vector(tags, feature_index)

    palette_idx = feature_index.index(("palette", "warm neutrals"))
    assert vec[palette_idx] == pytest.approx(0.9)


def test_feature_vector_ignores_unknown_categories() -> None:
    feature_index = build_feature_index()
    tags = [
        ExtractedTag(category="mood", value="happy", confidence=1.0, evidence=""),
    ]

    vec = feature_vector(tags, feature_index)

    assert not np.any(vec)


def _tiny_bundle() -> LearnedVibeBundle:
    """Train a one-feature logreg that separates two synthetic classes."""
    feature_index = build_feature_index()
    n_features = len(feature_index)
    cottage_idx = feature_index.index(("texture", "linen"))
    grunge_idx = feature_index.index(("texture", "distressed"))

    rng = np.random.default_rng(0)
    n_per_class = 20
    X = np.zeros((n_per_class * 2, n_features), dtype=np.float32)
    y: list[str] = []
    for i in range(n_per_class):
        X[i, cottage_idx] = 0.8 + rng.uniform(-0.1, 0.1)
        y.append("cottagecore")
    for i in range(n_per_class, 2 * n_per_class):
        X[i, grunge_idx] = 0.8 + rng.uniform(-0.1, 0.1)
        y.append("grunge")

    model = train_logreg(X, np.array(y))
    return LearnedVibeBundle(
        model=model,
        feature_index=feature_index,
        label_classes=list(model.classes_),
        metadata={"n_train": 2 * n_per_class},
    )


def test_predict_topk_ranks_matching_class_first() -> None:
    bundle = _tiny_bundle()
    feature_index = bundle.feature_index
    cottage_vec = np.zeros(len(feature_index), dtype=np.float32)
    cottage_vec[feature_index.index(("texture", "linen"))] = 0.9

    top = predict_topk(bundle.model, bundle.label_classes, cottage_vec, k=2)

    assert len(top) == 2
    assert top[0][0] == "cottagecore"
    assert 0.0 <= top[0][1] <= 1.0
    assert top[0][1] >= top[1][1]


def test_score_vibes_learned_matches_catalog_shape() -> None:
    """The learned scorer should still return one VibeScore per catalog vibe."""
    from vibecheck.vibe.catalog import VIBE_PROFILES

    bundle = _tiny_bundle()
    tags = [
        ExtractedTag(category="texture", value="linen", confidence=0.9, evidence=""),
    ]

    scores, notes = score_vibes_learned(tags, bundle)

    assert {s.vibe for s in scores} == {p.name for p in VIBE_PROFILES}
    top = scores[0]
    assert top.vibe == "cottagecore"
    assert top.score > 0
    untrained = [s.vibe for s in scores if s.vibe not in bundle.label_classes]
    assert all(s.score == 0.0 for s in scores if s.vibe in [u for u in untrained])
    assert any("no training data" in n for n in notes)


def test_score_vibes_learned_handles_empty_features() -> None:
    bundle = _tiny_bundle()

    scores, notes = score_vibes_learned([], bundle)

    assert all(s.score == 0.0 for s in scores)
    assert any("zero scores" in n for n in notes)


def test_save_and_load_bundle_roundtrip(tmp_path: Path) -> None:
    original = _tiny_bundle()
    path = tmp_path / "bundle.joblib"

    save_bundle(original, path)
    reloaded = load_bundle(path)

    assert reloaded.label_classes == original.label_classes
    assert reloaded.feature_index == original.feature_index
    assert reloaded.metadata["n_train"] == original.metadata["n_train"]
    cottage_vec = np.zeros(len(reloaded.feature_index), dtype=np.float32)
    cottage_vec[reloaded.feature_index.index(("texture", "linen"))] = 0.9
    top = predict_topk(reloaded.model, reloaded.label_classes, cottage_vec, k=1)
    assert top[0][0] == "cottagecore"


def test_load_bundle_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(LearnedVibeError):
        load_bundle(tmp_path / "does_not_exist.joblib")


def test_learned_classifier_outperforms_hand_weighted_on_held_out_feature() -> None:
    """Sanity check: the learned model gets the right answer where hand weights miss.

    The hand-weighted scorer requires the exact catalog keyword to appear in
    the tag list. A row with only ``texture:linen`` doesn't hit any
    grunge keyword, so hand weights rank grunge below cottagecore. The
    classifier learns this association from the training data.
    """
    bundle = _tiny_bundle()
    grunge_tags = [
        ExtractedTag(
            category="texture", value="distressed", confidence=0.9, evidence=""
        ),
    ]

    learned_scores, _ = score_vibes_learned(grunge_tags, bundle)
    hand_scores, _ = score_vibes(grunge_tags)

    learned_top = learned_scores[0]
    hand_top = hand_scores[0]
    assert learned_top.vibe == "grunge"
    assert learned_top.score > hand_top.score or hand_top.vibe != "grunge"
