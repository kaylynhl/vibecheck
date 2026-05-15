"""Tests for the audio-feature profile + scorer.

These cover the small pieces of logic in ``vibecheck.rec.spotify_audio``:
profile lookup with fuzzy aesthetic names, visual-tag nudges, and the
scalar audio_score that the playlist re-ranker depends on.
"""

from __future__ import annotations

from vibecheck.rec.spotify_audio import (
    AESTHETIC_AUDIO_PROFILES,
    VISUAL_TAG_NUDGES,
    _normalise_feature,
    apply_visual_tag_nudges,
    audio_score,
    get_profile,
)
from vibecheck.schemas import ExtractedTag


def test_all_original_eight_aesthetics_have_profiles() -> None:
    """The CLIP-LoRA evaluation classes must each have an audio profile so
    the playlist module never falls back to text-only for those vibes."""
    for cls in (
        "minimalist",
        "dark_academia",
        "cottagecore",
        "grunge",
        "coastal_grandmother",
        "scandinavian",
        "mid_century_modern",
        "japandi",
    ):
        assert cls in AESTHETIC_AUDIO_PROFILES, cls


def test_get_profile_handles_casing_spaces_and_dashes() -> None:
    """Groq vision returns aesthetic strings in many formats. The lookup
    should normalise them all to the profile dict's snake_case keys."""
    target = AESTHETIC_AUDIO_PROFILES["dark_academia"]
    assert get_profile("dark_academia") is target
    assert get_profile("Dark Academia") is target
    assert get_profile("dark-academia") is target
    assert get_profile("DARK_ACADEMIA") is target


def test_get_profile_returns_none_for_unknown_aesthetic() -> None:
    assert get_profile("") is None
    assert get_profile("not_a_real_vibe") is None


def test_normalise_feature_clamps_raw_unit_values() -> None:
    # tempo bounds are 0-220; loudness is -60-0
    assert _normalise_feature("tempo", 110) == 0.5
    assert _normalise_feature("tempo", 9999) == 1.0
    assert _normalise_feature("tempo", -5) == 0.0
    assert _normalise_feature("loudness", -30) == 0.5
    # [0,1] features are returned as-is (clamped)
    assert _normalise_feature("valence", 0.4) == 0.4
    assert _normalise_feature("valence", 1.5) == 1.0


def test_audio_score_is_higher_for_matching_track() -> None:
    """A track that matches dark_academia's profile must outscore one that
    matches its opposite."""
    matching = {
        "valence": 0.22,
        "energy": 0.35,
        "acousticness": 0.78,
        "instrumentalness": 0.72,
        "danceability": 0.32,
        "tempo": 92.0,
    }
    opposite = {
        "valence": 0.95,
        "energy": 0.95,
        "acousticness": 0.05,
        "instrumentalness": 0.05,
        "danceability": 0.90,
        "tempo": 145.0,
    }
    assert audio_score(matching, "dark_academia") > audio_score(opposite, "dark_academia")


def test_audio_score_returns_zero_when_features_missing() -> None:
    """If the track has no features at all, the scorer cannot rank it and
    must return 0.0 so callers fall back to text-only."""
    assert audio_score({}, "dark_academia") == 0.0
    assert audio_score(None, "dark_academia") == 0.0


def test_audio_score_returns_zero_for_unknown_aesthetic() -> None:
    """Unknown aesthetics turn off the audio re-rank entirely."""
    features = {"valence": 0.5, "energy": 0.5, "acousticness": 0.5}
    assert audio_score(features, "not_a_real_vibe") == 0.0


def test_visual_tag_nudges_shift_target_in_expected_direction() -> None:
    base = AESTHETIC_AUDIO_PROFILES["dark_academia"]
    # "dim" lighting should lower valence
    nudged = apply_visual_tag_nudges(
        base, [ExtractedTag(category="lighting", value="dim", confidence=1.0, evidence="")]
    )
    assert nudged["valence"][0] < base["valence"][0]
    # weights must not change
    assert nudged["valence"][1] == base["valence"][1]


def test_visual_tag_nudges_can_add_new_feature() -> None:
    """When a nudge mentions a feature the base profile doesn't include,
    it should still be applied with a starter weight."""
    base = AESTHETIC_AUDIO_PROFILES["minimalist"]
    nudged = apply_visual_tag_nudges(
        base, [ExtractedTag(category="palette", value="vibrant", confidence=1.0, evidence="")]
    )
    # "vibrant" bumps energy + danceability; minimalist profile has energy
    # already but no danceability. The latter should now appear.
    assert "danceability" in nudged
    assert nudged["danceability"][0] > 0


def test_visual_tag_nudges_ignore_unknown_tags() -> None:
    """Tags that aren't in the nudge table are silent no-ops."""
    base = AESTHETIC_AUDIO_PROFILES["grunge"]
    nudged = apply_visual_tag_nudges(
        base, [ExtractedTag(category="pattern", value="paisley", confidence=1.0, evidence="")]
    )
    assert nudged == base


def test_visual_tag_nudge_keys_use_only_known_categories() -> None:
    """The nudge dict's category tokens must overlap with the extracted-tag
    vocabulary so they can actually fire in production."""
    from vibecheck.tags.vocabulary import TAG_CATEGORIES

    used_categories = {cat for (cat, _) in VISUAL_TAG_NUDGES}
    unknown = used_categories - set(TAG_CATEGORIES)
    assert not unknown, f"Unknown tag categories in nudges: {unknown}"
