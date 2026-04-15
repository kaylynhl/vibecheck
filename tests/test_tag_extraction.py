from __future__ import annotations

import pytest

from vibecheck.errors import TagExtractionError
from vibecheck.tags.extract import extract_structured_tags


def test_extract_structured_tags_for_room_description() -> None:
    description = (
        "A cozy room with warm neutrals, natural light, woven textures, floral details, "
        "wood furniture, and plenty of natural fibers."
    )

    tags = extract_structured_tags(description)
    values = {tag.value for tag in tags}

    assert "cozy" in values
    assert "warm neutrals" in values
    assert "natural" in values
    assert "woven" in values
    assert "floral" in values
    assert "wood" in values


def test_extract_structured_tags_for_outfit_description() -> None:
    description = (
        "The outfit feels sleek and polished with a fitted silhouette, cream tones, "
        "smooth fabric, and solid minimal styling."
    )

    tags = extract_structured_tags(description)
    values = {tag.value for tag in tags}

    assert "sleek" in values
    assert "fitted" in values
    assert "cream" in values
    assert "smooth" in values
    assert "solid" in values


def test_extract_structured_tags_uses_inferred_hints() -> None:
    description = "The room is sunlit, homey, and filled with oak surfaces."

    tags = extract_structured_tags(description)
    values = {tag.value for tag in tags}

    assert "natural" in values
    assert "cozy" in values
    assert "wood" in values


def test_extract_structured_tags_returns_empty_list_for_unmatched_description() -> None:
    description = "A scene with unusual forms, atmospheric energy, and surreal visual tension."

    tags = extract_structured_tags(description)

    assert tags == []


def test_extract_structured_tags_rejects_blank_description() -> None:
    with pytest.raises(TagExtractionError):
        extract_structured_tags("   ")
