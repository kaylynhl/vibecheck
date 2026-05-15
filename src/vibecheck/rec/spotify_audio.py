"""Audio-feature scoring for the playlist re-ranker.

Each aesthetic in our taxonomy has a hand-crafted *audio profile* -- a small
set of Spotify audio features (valence, energy, acousticness, ...) with target
values and weights that describe what music in that aesthetic tends to sound
like. The audio scorer measures how well a candidate track's actual feature
vector matches the target profile.

This complements the FashionBERT text re-ranker in ``playlists.py``: text
captures semantic / cultural fit (song titles, artists, genres), audio
captures acoustic fit (it actually sounds moody / acoustic / danceable).

The profile dictionary is hand-tuned data, not learned. Visual-tag nudges let
the same aesthetic produce slightly different rankings depending on the
specific photo (e.g. a dark dark-academia coffee shop biases toward lower
valence, a warmer one biases toward higher acousticness).
"""

from __future__ import annotations

from typing import Iterable

from vibecheck.schemas import ExtractedTag


# (feature_target, weight). Targets are on the same scale Spotify reports:
#   * Most features are already in [0, 1]
#   * ``loudness`` is in dB (roughly -60 to 0)
#   * ``tempo`` is in BPM (roughly 50 to 210)
# The scorer normalises both targets and observed values to [0, 1] before
# computing distance, so the units below are intentionally raw.
AESTHETIC_AUDIO_PROFILES: dict[str, dict[str, tuple[float, float]]] = {
    # ── original 8 (CLIP-LoRA classes) ──────────────────────────────────
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
    # ── extended ────────────────────────────────────────────────────────
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


# Visual-tag-driven adjustments to the base profile. Keys are
# (tag_category, tag_value) tuples drawn from the existing extracted_tags
# vocabulary in ``vibecheck.tags.vocabulary``. Values are feature deltas
# that get added to the profile *target* before scoring, letting the same
# aesthetic produce different playlists for different photos.
VISUAL_TAG_NUDGES: dict[tuple[str, str], dict[str, float]] = {
    # lighting -> mood / brightness
    ("lighting", "dim"):     {"valence": -0.10, "energy": -0.05},
    ("lighting", "moody"):   {"valence": -0.10, "energy": -0.05},
    ("lighting", "bright"):  {"valence": +0.10, "energy": +0.05},
    ("lighting", "natural"): {"valence": +0.05, "energy": +0.05},
    ("lighting", "warm"):    {"acousticness": +0.15, "valence": +0.05},
    ("lighting", "cool"):    {"acousticness": -0.10, "valence": -0.05},
    ("lighting", "candlelit"): {"valence": -0.05, "acousticness": +0.10},
    # palette -> warmth / saturation
    ("palette", "dark and moody"): {"valence": -0.10, "energy": -0.05},
    ("palette", "light and airy"): {"valence": +0.10, "energy": +0.05},
    ("palette", "warm neutrals"):  {"acousticness": +0.10, "valence": +0.05},
    ("palette", "earth tones"):    {"acousticness": +0.10, "valence": +0.05},
    ("palette", "cool neutrals"):  {"acousticness": -0.05, "valence": -0.05},
    ("palette", "vibrant"):        {"energy": +0.10, "danceability": +0.05},
    ("palette", "muted"):          {"energy": -0.10, "instrumentalness": +0.10},
    ("palette", "pastels"):        {"energy": -0.05, "valence": +0.05},
    # texture -> physical feel
    ("texture", "rough"):     {"energy": +0.10, "acousticness": -0.05},
    ("texture", "rustic"):    {"acousticness": +0.10, "energy": -0.05},
    ("texture", "smooth"):    {"instrumentalness": +0.05, "energy": -0.05},
    ("texture", "sleek"):     {"instrumentalness": +0.05, "energy": -0.05},
    ("texture", "polished"):  {"instrumentalness": +0.05, "energy": +0.05},
    ("texture", "rich"):      {"acousticness": +0.05, "valence": +0.05},
    ("texture", "cozy"):      {"acousticness": +0.10, "valence": +0.05},
}


# Hardcoded normalisation bounds for raw-unit features. Empirical min/max
# from the Kaggle catalog would be tighter, but the relative ordering of
# tracks within a re-rank window is what matters, not the absolute scores.
# Hardcoding keeps this module a pure data + math library: no CSV load
# required to call ``audio_score``.
_RAW_FEATURE_BOUNDS: dict[str, tuple[float, float]] = {
    "tempo":    (0.0, 220.0),
    "loudness": (-60.0, 0.0),
}


def _normalise_feature(feature: str, value: float) -> float:
    """Map raw audio-feature values onto [0, 1] for distance computation."""
    if feature not in _RAW_FEATURE_BOUNDS:
        # Already in [0, 1] per Spotify's API; clamp to be safe.
        return max(0.0, min(1.0, float(value)))
    lo, hi = _RAW_FEATURE_BOUNDS[feature]
    span = hi - lo
    if span <= 0:
        return 0.0
    return max(0.0, min(1.0, (float(value) - lo) / span))


def get_profile(aesthetic: str) -> dict[str, tuple[float, float]] | None:
    """Look up the audio profile for an aesthetic, with light fuzzy matching."""
    if not aesthetic:
        return None
    key = aesthetic.strip().lower().replace(" ", "_").replace("-", "_")
    direct = AESTHETIC_AUDIO_PROFILES.get(key)
    if direct is not None:
        return direct
    # Last resort: substring match against known keys. Picks the first hit
    # in declaration order, which biases toward the original 8 classes.
    for known in AESTHETIC_AUDIO_PROFILES:
        if known in key or key in known:
            return AESTHETIC_AUDIO_PROFILES[known]
    return None


def apply_visual_tag_nudges(
    profile: dict[str, tuple[float, float]],
    tags: Iterable[ExtractedTag],
) -> dict[str, tuple[float, float]]:
    """Return a copy of ``profile`` with deltas applied for matching tags.

    Each (category, value) tag is matched against ``VISUAL_TAG_NUDGES``; the
    delta is added to the target side of the (target, weight) tuple. Targets
    are clamped to [0, 1] after each nudge (raw-unit features are normalised
    later anyway, so working in normalised space here would be wrong).
    """
    nudged: dict[str, list[float]] = {f: [t, w] for f, (t, w) in profile.items()}
    for tag in tags:
        deltas = VISUAL_TAG_NUDGES.get((tag.category, tag.value))
        if not deltas:
            continue
        for feature, delta in deltas.items():
            if feature in nudged:
                nudged[feature][0] = max(0.0, min(1.0, nudged[feature][0] + delta))
            else:
                # Tag wants to bias a feature the profile doesn't mention -- add
                # it with the delta as a target and a small starter weight.
                nudged[feature] = [max(0.0, min(1.0, delta)), 0.8]
    return {f: (t, w) for f, (t, w) in nudged.items()}


def audio_score(
    track_features: dict[str, float] | None,
    aesthetic: str,
    *,
    tags: Iterable[ExtractedTag] | None = None,
) -> float:
    """Return a [0, 1] similarity between a track's features and an aesthetic.

    Returns 0.0 -- a "no signal" sentinel -- when the aesthetic has no
    profile, the track has no features, or the aesthetic's profile shares
    no overlapping features with the track. Callers can treat 0.0 as
    "audio re-rank is inactive for this track" and fall back to the text
    score alone.
    """
    if not track_features:
        return 0.0
    profile = get_profile(aesthetic)
    if profile is None:
        return 0.0
    if tags is not None:
        profile = apply_visual_tag_nudges(profile, tags)

    used_weight = 0.0
    weighted_distance = 0.0
    for feature, (target, weight) in profile.items():
        observed = track_features.get(feature)
        if observed is None:
            continue
        norm_target = _normalise_feature(feature, target)
        norm_observed = _normalise_feature(feature, observed)
        weighted_distance += weight * abs(norm_target - norm_observed)
        used_weight += weight

    if used_weight <= 0:
        return 0.0
    similarity = 1.0 - (weighted_distance / used_weight)
    return max(0.0, min(1.0, similarity))
