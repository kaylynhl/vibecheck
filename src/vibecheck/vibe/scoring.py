"""Score candidate vibes against extracted structured tags."""

from __future__ import annotations

from typing import Literal

from vibecheck.schemas import ExtractedTag, VibeScore
from vibecheck.vibe.catalog import VIBE_PROFILES, VibeProfile

Mode = Literal["room", "outfit"]

_MODE_BONUS = 0.08


def score_vibes(
    tags: list[ExtractedTag],
    *,
    mode: Mode | None = None,
) -> tuple[list[VibeScore], list[str]]:
    """Score all vibe profiles and return sorted results plus confidence notes."""
    scores: list[VibeScore] = []
    for profile in VIBE_PROFILES:
        scores.append(_score_profile(profile, tags, mode=mode))

    ranked = sorted(scores, key=lambda score: (-score.score, score.vibe))
    notes = _build_confidence_notes(ranked, tags)
    return ranked, notes


def _score_profile(
    profile: VibeProfile,
    tags: list[ExtractedTag],
    *,
    mode: Mode | None,
) -> VibeScore:
    """Score one vibe profile against the extracted tags."""
    total_weight = sum(profile.keyword_weights.values()) + _MODE_BONUS
    raw_score = 0.0
    matched_keywords: list[str] = []

    for tag in tags:
        weight = profile.keyword_weights.get(tag.value)
        if weight is None:
            continue
        raw_score += weight * tag.confidence * 1.1
        matched_keywords.append(tag.value)

    if mode and profile.mode_bias in {mode, "both"}:
        raw_score += _MODE_BONUS

    normalized_score = min(raw_score / total_weight, 1.0) if total_weight else 0.0
    return VibeScore(
        vibe=profile.name,
        score=round(normalized_score, 4),
        matched_keywords=sorted(set(matched_keywords)),
        description=profile.description,
    )


def _build_confidence_notes(
    scores: list[VibeScore],
    tags: list[ExtractedTag],
) -> list[str]:
    """Generate simple confidence notes about the ranking quality."""
    notes: list[str] = []
    if len(tags) < 4:
        notes.append("Tag coverage is light, so vibe ranking may be underdetermined.")

    if scores:
        top = scores[0]
        second = scores[1] if len(scores) > 1 else None
        if top.score < 0.25:
            notes.append("No vibe achieved a strong score; the imagery may be visually mixed.")
        if second and abs(top.score - second.score) < 0.08:
            notes.append("The top two vibes are close, indicating an ambiguous or blended aesthetic.")

    low_confidence_count = sum(1 for tag in tags if tag.confidence < 0.7)
    if low_confidence_count >= max(2, len(tags) // 2):
        notes.append("Many extracted tags were inferred indirectly rather than matched explicitly.")

    tag_values = {tag.value for tag in tags}
    conflicts = (
        ({"minimal", "maximalist"}, "Both minimal and maximal cues are present."),
        ({"light and airy", "dark and moody"}, "Both airy and moody palette cues are present."),
        ({"tailored", "oversized"}, "Silhouette cues mix tailored and oversized styling."),
    )
    for required_values, message in conflicts:
        if required_values.issubset(tag_values):
            notes.append(message)

    return notes
