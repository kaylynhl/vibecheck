"""Audio-feature-based playlist retrieval using aesthetic profiles.

Scores tracks from the Spotify dataset against per-aesthetic audio feature
profiles and returns the top-k best matches. Integrates with the existing
vibe pipeline as a drop-in complement (or replacement) for the live
Spotify search in ``rec/playlists.py``.

"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]          # project root
DEFAULT_CSV   = ROOT / "spotify" / "spotify_data.csv"
DEFAULT_CACHE = ROOT / "data" / "processed" / "spotify_audio_index.json"

AESTHETIC_AUDIO_PROFILES: dict[str, dict[str, tuple[float, float]]] = {
    # ── original 8 (CLIP-LoRA classes) ──────────────────────────────────────
    "dark_academia": {
        "energy":           (0.35, 1.5),
        "acousticness":     (0.75, 1.5),
        "instrumentalness": (0.70, 1.2),
        "valence":          (0.25, 1.2),
        "tempo":            (95,   0.5),
        "danceability":     (0.35, 0.8),
    },
    "cottagecore": {
        "acousticness":     (0.85, 1.5),
        "energy":           (0.30, 1.2),
        "valence":          (0.65, 1.2),
        "instrumentalness": (0.40, 0.8),
        "tempo":            (90,   0.5),
    },
    "minimalist": {
        "instrumentalness": (0.80, 1.5),
        "energy":           (0.25, 1.2),
        "speechiness":      (0.03, 1.2),
        "loudness":         (-18,  1.0),
        "valence":          (0.40, 0.8),
    },
    "grunge": {
        "energy":           (0.85, 1.5),
        "loudness":         (-4,   1.3),
        "valence":          (0.25, 1.2),
        "acousticness":     (0.05, 1.0),
        "danceability":     (0.45, 0.8),
    },
    "coastal_grandmother": {
        "acousticness":     (0.70, 1.3),
        "valence":          (0.60, 1.2),
        "energy":           (0.35, 1.2),
        "tempo":            (85,   0.5),
        "instrumentalness": (0.30, 0.8),
    },
    "scandinavian": {
        "instrumentalness": (0.65, 1.5),
        "acousticness":     (0.55, 1.2),
        "energy":           (0.30, 1.2),
        "valence":          (0.45, 0.8),
        "loudness":         (-14,  0.8),
    },
    "mid_century_modern": {
        "instrumentalness": (0.60, 1.3),
        "acousticness":     (0.40, 1.0),
        "danceability":     (0.55, 1.2),
        "tempo":            (110,  0.8),
        "valence":          (0.55, 1.0),
    },
    "japandi": {
        "instrumentalness": (0.85, 1.5),
        "energy":           (0.20, 1.3),
        "acousticness":     (0.70, 1.2),
        "speechiness":      (0.03, 1.0),
        "valence":          (0.35, 0.8),
    },
    # ── extended ────────────────────────────────────────────────────
    "y2k": {
        "danceability":     (0.80, 1.5),
        "energy":           (0.85, 1.5),
        "valence":          (0.80, 1.3),
        "tempo":            (128,  1.0),
        "acousticness":     (0.05, 1.0),
        "speechiness":      (0.08, 0.8),
    },
    "indie_sleaze": {
        "energy":           (0.75, 1.3),
        "valence":          (0.45, 1.2),
        "danceability":     (0.65, 1.2),
        "acousticness":     (0.10, 1.0),
        "loudness":         (-5,   1.0),
        "speechiness":      (0.07, 0.8),
    },
    "soft_girl": {
        "valence":          (0.80, 1.5),
        "acousticness":     (0.55, 1.2),
        "energy":           (0.40, 1.2),
        "danceability":     (0.60, 1.0),
        "instrumentalness": (0.15, 0.8),
    },
    "clean_girl": {
        "energy":           (0.55, 1.2),
        "valence":          (0.65, 1.2),
        "danceability":     (0.70, 1.3),
        "acousticness":     (0.20, 1.0),
        "speechiness":      (0.05, 0.8),
        "loudness":         (-7,   0.8),
    },
    "old_money": {
        "instrumentalness": (0.55, 1.3),
        "acousticness":     (0.50, 1.2),
        "energy":           (0.30, 1.2),
        "valence":          (0.40, 1.0),
        "loudness":         (-12,  1.0),
        "tempo":            (88,   0.5),
    },
    "quiet_luxury": {
        "instrumentalness": (0.70, 1.5),
        "energy":           (0.22, 1.3),
        "acousticness":     (0.60, 1.2),
        "loudness":         (-15,  1.0),
        "speechiness":      (0.03, 1.0),
        "valence":          (0.38, 0.8),
    },
    "bohemian": {
        "acousticness":     (0.65, 1.3),
        "danceability":     (0.60, 1.2),
        "valence":          (0.65, 1.2),
        "energy":           (0.55, 1.0),
        "tempo":            (100,  0.6),
        "instrumentalness": (0.25, 0.8),
    },
    "cottagecore_dark": {
        "acousticness":     (0.70, 1.5),
        "valence":          (0.25, 1.3),
        "energy":           (0.35, 1.2),
        "instrumentalness": (0.50, 1.0),
        "mode":             (0.0,  1.0),
        "tempo":            (80,   0.5),
    },
    "streetwear": {
        "danceability":     (0.78, 1.5),
        "energy":           (0.80, 1.3),
        "speechiness":      (0.18, 1.3),
        "loudness":         (-4,   1.0),
        "valence":          (0.55, 0.8),
        "acousticness":     (0.05, 0.8),
    },
    "hypebeast": {
        "energy":           (0.90, 1.5),
        "danceability":     (0.80, 1.3),
        "speechiness":      (0.22, 1.3),
        "loudness":         (-3,   1.2),
        "valence":          (0.60, 0.8),
        "acousticness":     (0.03, 0.8),
    },
    "art_hoe": {
        "valence":          (0.55, 1.2),
        "acousticness":     (0.45, 1.2),
        "energy":           (0.50, 1.0),
        "danceability":     (0.55, 1.0),
        "instrumentalness": (0.20, 1.0),
        "speechiness":      (0.06, 0.8),
    },
    "normcore": {
        "valence":          (0.60, 1.2),
        "energy":           (0.55, 1.0),
        "danceability":     (0.60, 1.0),
        "acousticness":     (0.30, 0.8),
        "loudness":         (-8,   0.8),
        "instrumentalness": (0.10, 0.8),
    },
    "e_girl": {
        "energy":           (0.80, 1.3),
        "valence":          (0.35, 1.3),
        "danceability":     (0.70, 1.2),
        "loudness":         (-5,   1.0),
        "acousticness":     (0.05, 1.0),
        "speechiness":      (0.10, 0.8),
    },
    "coquette": {
        "valence":          (0.55, 1.3),
        "acousticness":     (0.50, 1.2),
        "energy":           (0.40, 1.2),
        "danceability":     (0.55, 1.0),
        "instrumentalness": (0.20, 0.8),
        "tempo":            (92,   0.5),
    },
    "twee": {
        "acousticness":     (0.75, 1.5),
        "valence":          (0.75, 1.3),
        "energy":           (0.35, 1.2),
        "instrumentalness": (0.20, 1.0),
        "danceability":     (0.50, 0.8),
        "tempo":            (85,   0.5),
    },
    "goblincore": {
        "acousticness":     (0.70, 1.3),
        "valence":          (0.40, 1.2),
        "energy":           (0.45, 1.2),
        "instrumentalness": (0.45, 1.0),
        "mode":             (0.0,  1.0),
        "tempo":            (95,   0.5),
    },
    "vaporwave": {
        "instrumentalness": (0.75, 1.5),
        "energy":           (0.30, 1.3),
        "danceability":     (0.55, 1.2),
        "valence":          (0.45, 1.0),
        "acousticness":     (0.10, 0.8),
        "tempo":            (80,   0.8),
    },
    "indie_folk": {
        "acousticness":     (0.85, 1.5),
        "energy":           (0.35, 1.3),
        "instrumentalness": (0.30, 1.0),
        "valence":          (0.45, 1.2),
        "tempo":            (92,   0.5),
        "danceability":     (0.40, 0.8),
    },
    "retro_70s": {
        "valence":          (0.70, 1.3),
        "danceability":     (0.68, 1.3),
        "energy":           (0.60, 1.0),
        "acousticness":     (0.35, 1.0),
        "tempo":            (105,  0.8),
        "instrumentalness": (0.25, 0.8),
    },
    "lo_fi": {
        "instrumentalness": (0.85, 1.5),
        "energy":           (0.25, 1.3),
        "acousticness":     (0.55, 1.2),
        "danceability":     (0.50, 1.0),
        "loudness":         (-14,  1.0),
        "valence":          (0.42, 0.8),
    },
}

_RAW_FEATURES = {"loudness", "tempo"}

_TAG_NUDGES: dict[tuple[str, str], dict[str, float]] = {
    ("brightness", "dark"):    {"valence": -0.10, "energy": -0.05},
    ("brightness", "bright"):  {"valence": +0.10, "energy": +0.05},
    ("warmth", "warm"):        {"acousticness": +0.15, "valence": +0.05},
    ("warmth", "cool"):        {"acousticness": -0.10, "valence": -0.05},
    ("saturation", "vivid"):   {"energy": +0.10, "danceability": +0.05},
    ("saturation", "muted"):   {"energy": -0.10, "instrumentalness": +0.10},
    ("clutter", "high"):       {"energy": +0.15, "danceability": +0.10},
    ("clutter", "low"):        {"instrumentalness": +0.10, "energy": -0.10},
    ("texture", "rough"):      {"energy": +0.10, "acousticness": -0.05},
    ("texture", "smooth"):     {"instrumentalness": +0.05, "energy": -0.05},
}


@dataclass
class AudioIndex:
    """In-memory index of normalised track features + raw metadata."""
    df: pd.DataFrame                       # full cleaned dataframe
    norm_df: pd.DataFrame                  # [0, 1]-normalised feature columns
    norm_stats: dict[str, tuple[float, float]]   # feature -> (min, max)
    feature_cols: list[str] = field(default_factory=list)


def _normalise(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, tuple[float, float]]]:
    """Min-max normalise raw-unit features; leave [0,1] features alone."""
    norm = df.copy()
    stats: dict[str, tuple[float, float]] = {}
    for col in _RAW_FEATURES:
        if col not in norm.columns:
            continue
        lo, hi = float(norm[col].min()), float(norm[col].max())
        stats[col] = (lo, hi)
        norm[col] = (norm[col] - lo) / (hi - lo + 1e-9)
    return norm, stats


def _normalise_target(feature: str, value: float,
                      stats: dict[str, tuple[float, float]]) -> float:
    """Apply the same normalisation to a profile target value."""
    if feature not in _RAW_FEATURES or feature not in stats:
        return value
    lo, hi = stats[feature]
    return (value - lo) / (hi - lo + 1e-9)


FEATURE_COLS = [
    "danceability", "energy", "key", "loudness", "mode",
    "speechiness", "acousticness", "instrumentalness",
    "liveness", "valence", "tempo",
]


def load_audio_index(
    csv_path: Path | str = DEFAULT_CSV,
    cache_path: Path | str | None = DEFAULT_CACHE,
    rebuild: bool = False,
) -> AudioIndex:
    """Load and normalise the Spotify dataset, with optional JSON cache.

    The cache stores only the normalisation stats (min/max per raw feature)
    so we can skip recomputing them. The full dataframe is always reloaded
    from the CSV — it's cheaper than serialising 170 MB of floats again.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Spotify CSV not found at {csv_path}. "
            "Check that spotify/spotify_data.csv is present locally "
            "(it is gitignored due to file size)."
        )

    df = pd.read_csv(csv_path)

    # Normalise column names: strip whitespace, lowercase
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    present_features = [c for c in FEATURE_COLS if c in df.columns]
    df = df.dropna(subset=present_features).reset_index(drop=True)

    # Load or compute normalisation stats
    cache_path = Path(cache_path) if cache_path else None
    if cache_path and cache_path.exists() and not rebuild:
        stats = json.loads(cache_path.read_text())
        norm_df = df.copy()
        for col, (lo, hi) in stats.items():
            if col in norm_df.columns:
                norm_df[col] = (norm_df[col] - lo) / (hi - lo + 1e-9)
    else:
        norm_df, stats = _normalise(df)
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(stats, indent=2))

    return AudioIndex(
        df=df,
        norm_df=norm_df,
        norm_stats=stats,
        feature_cols=present_features,
    )


def _apply_tag_nudges(
    profile: dict[str, tuple[float, float]],
    image_tags: dict[str, str],
) -> dict[str, tuple[float, float]]:
    """Return a copy of the profile with CLIP visual tag nudges applied."""
    nudged = {k: list(v) for k, v in profile.items()}
    for (cat, val), deltas in _TAG_NUDGES.items():
        if image_tags.get(cat) == val:
            for feature, delta in deltas.items():
                if feature in nudged:
                    nudged[feature][0] = float(
                        np.clip(nudged[feature][0] + delta, 0.0, 1.0)
                    )
                else:
                    nudged[feature] = [float(np.clip(delta, 0.0, 1.0)), 0.8]
    return {k: tuple(v) for k, v in nudged.items()}  # type: ignore[return-value]


def score_tracks(
    aesthetic: str,
    index: AudioIndex,
    top_k: int = 10,
    image_tags: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
   
    profile = AESTHETIC_AUDIO_PROFILES.get(aesthetic)
    if profile is None:
        # Fuzzy fallback: try underscore/hyphen/space variants
        key = aesthetic.lower().replace(" ", "_").replace("-", "_")
        profile = AESTHETIC_AUDIO_PROFILES.get(key)
    if profile is None:
        raise KeyError(
            f"No audio profile for aesthetic '{aesthetic}'. "
            f"Available: {sorted(AESTHETIC_AUDIO_PROFILES)}"
        )

    if image_tags:
        profile = _apply_tag_nudges(profile, image_tags)

    total_weight = sum(w for _, w in profile.values())
    scores = np.zeros(len(index.norm_df), dtype=np.float64)

    for feature, (target, weight) in profile.items():
        if feature not in index.norm_df.columns:
            continue
        norm_target = _normalise_target(feature, target, index.norm_stats)
        scores += weight * (1.0 - np.abs(index.norm_df[feature].to_numpy() - norm_target))

    scores /= total_weight

    top_idx = np.argpartition(scores, -top_k)[-top_k:]
    top_idx = top_idx[np.argsort(-scores[top_idx])]

    results: list[dict[str, Any]] = []
    for i in top_idx:
        row = index.df.iloc[i]
        audio_features = {
            f: float(row[f]) for f in index.feature_cols if f in index.df.columns
        }
        results.append({
            "artist_name":    str(row.get("artist_name", "")),
            "track_name":     str(row.get("track_name", "")),
            "track_id":       str(row.get("track_id", "")),
            "genre":          str(row.get("genre", "")),
            "year":           int(row["year"]) if "year" in row else None,
            "popularity":     int(row["popularity"]) if "popularity" in row else None,
            "vibe_score":     float(scores[i]),
            "audio_features": audio_features,
        })
    return results


def get_profile_for_vibe(aesthetic: str) -> dict[str, tuple[float, float]] | None:
    """Convenience accessor used by the pipeline and tests."""
    key = aesthetic.lower().replace(" ", "_").replace("-", "_")
    return AESTHETIC_AUDIO_PROFILES.get(key)