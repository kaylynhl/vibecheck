from __future__ import annotations

from vibecheck.schemas import ExtractedTag
from vibecheck.vibe.scoring import score_vibes


def test_score_vibes_ranks_cottagecore_for_matching_room_tags() -> None:
    tags = [
        ExtractedTag(category="palette", value="warm neutrals", confidence=0.95, evidence="warm neutrals"),
        ExtractedTag(category="texture", value="cozy", confidence=0.92, evidence="cozy"),
        ExtractedTag(category="pattern", value="floral", confidence=0.88, evidence="floral"),
        ExtractedTag(category="material", value="wood", confidence=0.9, evidence="wood"),
    ]

    scores, notes = score_vibes(tags, mode="room")

    assert scores[0].vibe == "cottagecore"
    assert scores[0].score > 0
    assert isinstance(notes, list)


def test_score_vibes_ranks_clean_girl_for_matching_outfit_tags() -> None:
    tags = [
        ExtractedTag(category="texture", value="sleek", confidence=0.95, evidence="sleek"),
        ExtractedTag(category="silhouette", value="fitted", confidence=0.92, evidence="fitted"),
        ExtractedTag(category="palette", value="cream", confidence=0.88, evidence="cream"),
        ExtractedTag(category="pattern", value="solid", confidence=0.8, evidence="solid"),
    ]

    scores, _ = score_vibes(tags, mode="outfit")

    assert scores[0].vibe == "clean girl"


def test_score_vibes_adds_ambiguity_note_for_close_scores() -> None:
    tags = [
        ExtractedTag(category="palette", value="warm neutrals", confidence=0.7, evidence="warm neutrals"),
        ExtractedTag(category="texture", value="minimal", confidence=0.72, evidence="minimal"),
        ExtractedTag(category="material", value="wood", confidence=0.68, evidence="wood"),
        ExtractedTag(category="lighting", value="natural", confidence=0.66, evidence="natural"),
    ]

    _, notes = score_vibes(tags, mode="room")

    assert any("close" in note for note in notes)
