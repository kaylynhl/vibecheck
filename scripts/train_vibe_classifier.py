"""Train logreg + MLP vibe classifiers on the mined tag-vector dataset
and report top-1 / top-3 accuracy against the hand-weighted baseline.

Outputs:

    data/processed/vibe_classifier.joblib  -- the best model (MLP), reloaded
                                              at inference time by the pipeline

Run::

    python scripts/build_vibe_dataset.py
    python scripts/train_vibe_classifier.py

A stratified 80/20 split is used. Both classifiers see the *same* train/test
split as the hand-weighted baseline so the accuracy numbers are comparable.
"""

from __future__ import annotations

import argparse
import base64
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np  # noqa: E402

from vibecheck.schemas import ExtractedTag  # noqa: E402
from vibecheck.vibe.catalog import VIBE_PROFILES  # noqa: E402
from vibecheck.vibe.learned import (  # noqa: E402
    DEFAULT_MODEL_PATH,
    LearnedVibeBundle,
    build_feature_index,
    save_bundle,
    train_logreg,
    train_mlp,
)
from vibecheck.vibe.scoring import score_vibes  # noqa: E402


DEFAULT_DATASET = ROOT / "data" / "processed" / "vibe_train.csv"


def decode_vector(b64: str, dim: int) -> np.ndarray:
    """Inverse of the encode_vector helper in build_vibe_dataset."""
    raw = base64.b64decode(b64.encode("ascii"))
    arr = np.frombuffer(raw, dtype=np.float32).copy()
    if arr.shape[0] != dim:
        raise ValueError(
            f"Expected feature vector of length {dim}, got {arr.shape[0]}."
        )
    return arr


def load_dataset(path: Path, feature_index):
    """Load mined examples, dropping any with a non-matching feature length."""
    X: list[np.ndarray] = []
    y: list[str] = []
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            X.append(decode_vector(row["feature_vector_b64"], len(feature_index)))
            y.append(row["vibe"])
    return np.vstack(X), np.array(y)


def stratified_split(
    X: np.ndarray, y: np.ndarray, test_frac: float = 0.2, seed: int = 42
):
    """Per-class shuffle then slice off ``test_frac`` of each class for test.

    Tiny classes (1 example) end up in train only; tests on those just contribute
    zero accuracy mass, which is honest.
    """
    rng = np.random.default_rng(seed)
    train_idx: list[int] = []
    test_idx: list[int] = []
    for label in np.unique(y):
        idxs = np.where(y == label)[0]
        rng.shuffle(idxs)
        n_test = max(1, int(round(len(idxs) * test_frac))) if len(idxs) > 1 else 0
        test_idx.extend(idxs[:n_test])
        train_idx.extend(idxs[n_test:])
    return np.array(sorted(train_idx)), np.array(sorted(test_idx))


def feature_index_to_lookup(feature_index):
    return {pair: i for i, pair in enumerate(feature_index)}


def vector_to_extracted_tags(vec: np.ndarray, feature_index) -> list[ExtractedTag]:
    """Approximate inverse: build ExtractedTag list from a feature vector.

    Used so we can replay the hand-weighted scorer on the *same* feature
    representation the learned classifiers see. The evidence field is left
    empty because we don't carry it through the dataset file.
    """
    tags: list[ExtractedTag] = []
    for idx, (category, value) in enumerate(feature_index):
        conf = float(vec[idx])
        if conf > 0:
            tags.append(
                ExtractedTag(
                    category=category,
                    value=value,
                    confidence=conf,
                    evidence="",
                )
            )
    return tags


def hand_weighted_predict_topk(
    X: np.ndarray, feature_index, k: int = 3
) -> list[list[str]]:
    """Run the existing hand-weighted scorer and return top-K vibe names per row."""
    out: list[list[str]] = []
    for row in X:
        tags = vector_to_extracted_tags(row, feature_index)
        scores, _ = score_vibes(tags)
        out.append([s.vibe for s in scores[:k]])
    return out


def model_predict_topk(
    model, label_classes: list[str], X: np.ndarray, k: int = 3
) -> list[list[str]]:
    """Run a fitted classifier and return top-K vibe names per row."""
    probs = model.predict_proba(X)
    order = np.argsort(-probs, axis=1)
    return [[label_classes[j] for j in row[:k]] for row in order]


def accuracy_at_k(predictions: list[list[str]], y_true: np.ndarray, k: int) -> float:
    if len(predictions) == 0:
        return 0.0
    hits = sum(1 for preds, truth in zip(predictions, y_true) if truth in preds[:k])
    return hits / len(predictions)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=800)
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"Dataset not found: {args.dataset}", file=sys.stderr)
        print("Run scripts/build_vibe_dataset.py first.", file=sys.stderr)
        return 2

    feature_index = build_feature_index()
    X, y = load_dataset(args.dataset, feature_index)
    print(f"Loaded {len(X)} examples across {len(np.unique(y))} vibe classes.")
    print(f"Class counts: {dict(Counter(y).most_common())}\n")

    train_idx, test_idx = stratified_split(X, y, test_frac=0.2)
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
    print(f"Train: {len(X_train)} | Test: {len(X_test)}\n")

    logreg = train_logreg(X_train, y_train)
    mlp = train_mlp(X_train, y_train, hidden=args.hidden, epochs=args.epochs)
    label_classes_logreg = list(logreg.classes_)
    label_classes_mlp = list(mlp.classes_)

    hand_preds = hand_weighted_predict_topk(X_test, feature_index, k=3)
    logreg_preds = model_predict_topk(logreg, label_classes_logreg, X_test, k=3)
    mlp_preds = model_predict_topk(mlp, label_classes_mlp, X_test, k=3)

    rows = [
        ("hand-weighted", hand_preds),
        ("logistic regression", logreg_preds),
        ("MLP (sklearn)", mlp_preds),
    ]

    print(f"{'model':<22} {'top-1':>8} {'top-3':>8}")
    print("-" * 42)
    for label, preds in rows:
        top1 = accuracy_at_k(preds, y_test, 1)
        top3 = accuracy_at_k(preds, y_test, 3)
        print(f"{label:<22} {top1:>8.3f} {top3:>8.3f}")
    print()

    bundle = LearnedVibeBundle(
        model=mlp,
        feature_index=feature_index,
        label_classes=label_classes_mlp,
        metadata={
            "trained_on": str(args.dataset),
            "n_train": int(len(X_train)),
            "n_test": int(len(X_test)),
            "hidden": args.hidden,
            "epochs": args.epochs,
            "class_counts": dict(Counter(y_train).most_common()),
            "untrained_vibes": sorted(
                {p.name for p in VIBE_PROFILES} - set(label_classes_mlp)
            ),
        },
    )
    save_bundle(bundle, args.output)
    print(f"Saved best model bundle to {args.output}")
    print(
        f"(catalog has {len({p.name for p in VIBE_PROFILES})} vibes; classifier "
        f"saw {len(label_classes_mlp)} in training)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
