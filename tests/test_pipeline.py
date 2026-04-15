from __future__ import annotations

from vibecheck.pipeline import analyze_images, analyze_images_to_dict


class StubVisionClient:
    def __init__(self, description: str, model: str = "stub-model") -> None:
        self.description = description
        self.model = model

    def analyze_images(self, images, *, mode=None) -> str:
        assert images
        return self.description


def test_analyze_images_end_to_end() -> None:
    client = StubVisionClient(
        "A cozy room with warm neutrals, natural light, woven textures, floral details, and wood furniture."
    )

    result = analyze_images([b"\xff\xd8\xfffake"], mode="room", client=client)

    assert result.raw_description
    assert result.extracted_tags
    assert result.vibe_scores
    assert result.top_vibes
    assert result.debug.model == "stub-model"


def test_analyze_images_to_dict_returns_json_ready_shape() -> None:
    client = StubVisionClient(
        "A sleek fitted outfit with cream tones, smooth fabric, and solid styling."
    )

    result = analyze_images_to_dict([b"\xff\xd8\xfffake"], mode="outfit", client=client)

    assert set(result.keys()) == {
        "raw_description",
        "extracted_tags",
        "vibe_scores",
        "top_vibes",
        "confidence_notes",
        "debug",
    }
    assert isinstance(result["extracted_tags"], list)
    assert isinstance(result["debug"], dict)


def test_analyze_images_handles_unmatched_description_gracefully() -> None:
    client = StubVisionClient(
        "A surreal composition with ambiguous forms and cinematic atmosphere."
    )

    result = analyze_images([b"\xff\xd8\xfffake"], mode="room", client=client)

    assert result.extracted_tags == []
    assert result.vibe_scores
    assert result.top_vibes
    assert any("No normalized tags were extracted" in note for note in result.confidence_notes)
    assert any("No normalized tags were extracted" in warning for warning in result.debug.warnings)
