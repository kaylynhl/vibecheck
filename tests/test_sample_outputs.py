from __future__ import annotations

import json
from pathlib import Path


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
EXPECTED_TOP_LEVEL_KEYS = {
    "raw_description",
    "extracted_tags",
    "vibe_scores",
    "top_vibes",
    "confidence_notes",
    "debug",
    "item_recommendations",
}


def test_sample_room_analysis_has_expected_shape() -> None:
    payload = json.loads((FIXTURES_DIR / "sample_room_analysis.json").read_text())

    assert set(payload.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert isinstance(payload["extracted_tags"], list)
    assert isinstance(payload["debug"], dict)


def test_sample_outfit_analysis_has_expected_shape() -> None:
    payload = json.loads((FIXTURES_DIR / "sample_outfit_analysis.json").read_text())

    assert set(payload.keys()) == EXPECTED_TOP_LEVEL_KEYS
    assert isinstance(payload["top_vibes"], list)
    assert isinstance(payload["confidence_notes"], list)
