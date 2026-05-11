"""Learned tags-to-vibe classifiers used as an alternative to the
hand-weighted scoring in ``vibe.scoring``.

The pipeline keeps the hand-weighted baseline as the default so the system
works without any trained checkpoint on disk. When a trained joblib is
present at ``data/processed/vibe_classifier.joblib`` and the caller opts in,
``score_vibes_learned`` returns the classifier's probabilities instead.

Why scikit-learn and not PyTorch:
    The proposal mentioned a small MLP; we use sklearn's MLPClassifier here.
    Same backprop, same hidden-layer story, but no extra torch dependency
    and the model serializes cleanly with joblib. We can swap in a torch
    model later without touching the call sites.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from vibecheck.errors import VibecheckError
from vibecheck.schemas import ExtractedTag, VibeScore
from vibecheck.tags.vocabulary import TAG_VOCABULARY
from vibecheck.vibe.catalog import VIBE_PROFILES


DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "processed" / "vibe_classifier.joblib"
)


class LearnedVibeError(VibecheckError):
    """Raised when the learned classifier is requested but cannot be loaded."""


@dataclass
class LearnedVibeBundle:
    """A trained classifier plus the inputs needed to use it at runtime."""

    model: Any
    feature_index: list[tuple[str, str]]
    label_classes: list[str]
    metadata: dict[str, Any]


def build_feature_index() -> list[tuple[str, str]]:
    """Stable, alphabetized list of (category, value) pairs used as the feature axis."""
    pairs: list[tuple[str, str]] = []
    for category in sorted(TAG_VOCABULARY):
        for value in sorted(TAG_VOCABULARY[category]):
            pairs.append((category, value))
    return pairs


def feature_vector(
    tags: list[ExtractedTag],
    feature_index: list[tuple[str, str]] | None = None,
) -> np.ndarray:
    """Pack a tag list into a fixed-length confidence vector.

    Each slot ``i`` corresponds to ``feature_index[i]`` (a (category, value)
    pair); the value is the highest confidence seen for that tag, or 0 if
    absent. This mirrors what the training-data builder produces, so the
    classifier sees the same feature distribution at train and inference time.
    """
    feature_index = feature_index or build_feature_index()
    lookup = {pair: i for i, pair in enumerate(feature_index)}
    vec = np.zeros(len(feature_index), dtype=np.float32)
    for tag in tags:
        idx = lookup.get((tag.category, tag.value))
        if idx is None:
            continue
        vec[idx] = max(vec[idx], float(tag.confidence))
    return vec


def train_logreg(X: np.ndarray, y: np.ndarray) -> Any:
    """Train a one-vs-rest logistic regression baseline."""
    from sklearn.linear_model import LogisticRegression

    # Small dataset, many features -> raise max_iter so lbfgs actually
    # converges. With >2 classes lbfgs defaults to multinomial in sklearn 1.5+.
    model = LogisticRegression(
        max_iter=2000,
        solver="lbfgs",
        C=1.0,
        random_state=42,
    )
    model.fit(X, y)
    return model


def train_mlp(
    X: np.ndarray,
    y: np.ndarray,
    *,
    hidden: int = 64,
    epochs: int = 200,
) -> Any:
    """Train a small MLP classifier on the feature vectors."""
    from sklearn.neural_network import MLPClassifier

    model = MLPClassifier(
        hidden_layer_sizes=(hidden,),
        activation="relu",
        solver="adam",
        max_iter=epochs,
        random_state=42,
        early_stopping=False,
    )
    model.fit(X, y)
    return model


def predict_topk(
    model: Any,
    label_classes: list[str],
    tag_vector: np.ndarray,
    k: int = 3,
) -> list[tuple[str, float]]:
    """Return the top-K (vibe, probability) tuples for a single feature vector."""
    if tag_vector.ndim == 1:
        tag_vector = tag_vector[None, :]
    proba = model.predict_proba(tag_vector)[0]
    order = np.argsort(-proba)
    return [(label_classes[i], float(proba[i])) for i in order[:k]]


def score_vibes_learned(
    tags: list[ExtractedTag],
    bundle: LearnedVibeBundle,
) -> tuple[list[VibeScore], list[str]]:
    """Score every catalog vibe using the learned classifier.

    Vibes the classifier never saw during training are still returned, just
    with score 0.0 -- this keeps the response shape identical to the
    hand-weighted ``score_vibes`` so downstream code doesn't care which
    scorer ran.
    """
    vec = feature_vector(tags, bundle.feature_index)
    if not np.any(vec):
        notes = [
            "No matched tag features available; learned classifier defaulted to zero scores."
        ]
        return _zero_scores(), notes

    probs = bundle.model.predict_proba(vec[None, :])[0]
    proba_by_vibe = {bundle.label_classes[i]: float(probs[i]) for i in range(len(probs))}

    scores: list[VibeScore] = []
    for profile in VIBE_PROFILES:
        prob = proba_by_vibe.get(profile.name, 0.0)
        matched = sorted({tag.value for tag in tags if tag.value in profile.keyword_weights})
        scores.append(
            VibeScore(
                vibe=profile.name,
                score=round(prob, 4),
                matched_keywords=matched,
                description=profile.description,
            )
        )

    ranked = sorted(scores, key=lambda score: (-score.score, score.vibe))
    notes: list[str] = []
    untrained = [
        profile.name for profile in VIBE_PROFILES if profile.name not in bundle.label_classes
    ]
    if untrained:
        notes.append(
            f"Learned classifier has no training data for {len(untrained)} vibes; "
            "those are returned with score 0.0."
        )
    if ranked and ranked[0].score < 0.2:
        notes.append("Top learned vibe scored below 0.2; result is low-confidence.")
    return ranked, notes


def save_bundle(bundle: LearnedVibeBundle, path: Path) -> None:
    """Persist a trained bundle (model + feature index + labels + metadata)."""
    import joblib

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": bundle.model,
        "feature_index": bundle.feature_index,
        "label_classes": bundle.label_classes,
        "metadata": bundle.metadata,
    }
    joblib.dump(payload, path)


def load_bundle(path: Path | None = None) -> LearnedVibeBundle:
    """Load a trained bundle from disk. Raises if the file is missing or malformed."""
    import joblib

    path = path or DEFAULT_MODEL_PATH
    if not path.exists():
        raise LearnedVibeError(f"No learned vibe classifier found at {path}.")
    try:
        payload = joblib.load(path)
    except Exception as exc:
        raise LearnedVibeError(f"Failed to load learned vibe classifier: {exc}") from exc

    return LearnedVibeBundle(
        model=payload["model"],
        feature_index=list(payload["feature_index"]),
        label_classes=list(payload["label_classes"]),
        metadata=dict(payload.get("metadata", {})),
    )


def _zero_scores() -> list[VibeScore]:
    return [
        VibeScore(
            vibe=profile.name,
            score=0.0,
            matched_keywords=[],
            description=profile.description,
        )
        for profile in VIBE_PROFILES
    ]
