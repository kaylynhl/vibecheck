from __future__ import annotations

import pytest

from vibecheck.errors import VisionAPIError, VisionOutputFormatError
from vibecheck.pipeline import analyze_images, analyze_images_to_dict
from vibecheck.schemas import VisionAnalysisPayload


class StubVisionClient:
    def __init__(self, payload: VisionAnalysisPayload, model: str = "stub-model") -> None:
        self.payload = payload
        self.model = model

    def analyze_images(self, images, *, mode=None) -> VisionAnalysisPayload:
        assert images
        return self.payload


class FailingVisionClient:
    def __init__(self, error: Exception, model: str = "stub-model") -> None:
        self.error = error
        self.model = model

    def analyze_images(self, images, *, mode=None) -> VisionAnalysisPayload:
        raise self.error


def make_payload(
    *,
    scene_type: str,
    visual_summary: str,
    palette=None,
    lighting=None,
    textures=None,
    patterns=None,
    silhouette_or_shape=None,
    objects_or_items=None,
    mood_descriptors=None,
    aesthetic_descriptors=None,
    vibe_query: str = "",
    uncertainty_notes=None,
    observed_facts=None,
    uncertain_inferences=None,
) -> VisionAnalysisPayload:
    return VisionAnalysisPayload(
        scene_type=scene_type,
        visual_summary=visual_summary,
        palette=palette or [],
        lighting=lighting or [],
        textures=textures or [],
        patterns=patterns or [],
        silhouette_or_shape=silhouette_or_shape or [],
        objects_or_items=objects_or_items or [],
        mood_descriptors=mood_descriptors or [],
        aesthetic_descriptors=aesthetic_descriptors or [],
        vibe_query=vibe_query,
        uncertainty_notes=uncertainty_notes or [],
        observed_facts=observed_facts or [],
        uncertain_inferences=uncertain_inferences or [],
    )


def test_analyze_images_end_to_end() -> None:
    client = StubVisionClient(
        make_payload(
            scene_type="room",
            visual_summary="A cozy room with warm neutrals and wood furniture.",
            palette=["warm neutrals"],
            lighting=["natural"],
            textures=["woven"],
            patterns=["floral"],
            objects_or_items=["wood furniture"],
            mood_descriptors=["cozy"],
            aesthetic_descriptors=["cottagecore"],
            vibe_query="warm neutrals, natural light, woven textures, floral, wood",
            uncertainty_notes=["Some corners are partially obscured."],
        )
    )

    result = analyze_images([b"\xff\xd8\xfffake"], mode="room", client=client)

    assert result.raw_description
    assert result.extracted_tags
    assert result.vibe_scores
    assert result.top_vibes
    assert result.debug.model == "stub-model"


def test_analyze_images_to_dict_returns_json_ready_shape() -> None:
    client = StubVisionClient(
        make_payload(
            scene_type="outfit",
            visual_summary="A sleek fitted outfit with cream tones.",
            palette=["cream"],
            lighting=["natural"],
            textures=["smooth"],
            patterns=["solid"],
            silhouette_or_shape=["fitted"],
            mood_descriptors=["polished"],
            aesthetic_descriptors=["clean girl"],
            vibe_query="cream, smooth fabric, fitted silhouette, polished minimal outfit",
        )
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
        make_payload(
            scene_type="unclear",
            visual_summary="A surreal composition with ambiguous forms and cinematic atmosphere.",
            vibe_query="surreal, cinematic, ambiguous, atmospheric",
            uncertainty_notes=["The subject matter is visually ambiguous."],
        )
    )

    result = analyze_images([b"\xff\xd8\xfffake"], mode="room", client=client)

    assert result.extracted_tags == []
    assert result.vibe_scores
    assert result.top_vibes
    assert any("No normalized tags were extracted" in note for note in result.confidence_notes)
    assert any("No normalized tags were extracted" in warning for warning in result.debug.warnings)


def test_analyze_images_uses_vibe_query_and_structured_fields_for_tag_extraction() -> None:
    client = StubVisionClient(
        make_payload(
            scene_type="outfit",
            visual_summary="An outfit with minimal visible detail.",
            palette=["cream"],
            textures=["smooth"],
            patterns=["solid"],
            silhouette_or_shape=["fitted"],
            vibe_query="cream, smooth fabric, fitted silhouette, clean girl, solid minimal outfit",
        )
    )

    result = analyze_images([b"\xff\xd8\xfffake"], mode="outfit", client=client)

    assert {tag.value for tag in result.extracted_tags} >= {"cream", "smooth", "solid", "fitted"}


def test_analyze_images_adds_scene_mode_mismatch_note() -> None:
    client = StubVisionClient(
        make_payload(
            scene_type="room",
            visual_summary="A bright interior with warm neutrals.",
            palette=["warm neutrals"],
            lighting=["natural"],
            vibe_query="warm neutrals, bright room",
        )
    )

    result = analyze_images([b"\xff\xd8\xfffake"], mode="outfit", client=client)

    assert any("requested mode" in note for note in result.confidence_notes)
    assert any("did not match" in warning for warning in result.debug.warnings)


def test_analyze_images_handles_malformed_vision_output_gracefully() -> None:
    client = FailingVisionClient(
        VisionOutputFormatError("Groq vision output was not valid JSON.")
    )

    result = analyze_images([b"\xff\xd8\xfffake"], mode="room", client=client)

    assert result.raw_description == ""
    assert result.extracted_tags == []
    assert result.vibe_scores
    assert result.top_vibes
    assert result.debug.validation_passed is False
    assert result.debug.parse_error == "Groq vision output was not valid JSON."
    assert any("malformed or invalid" in note for note in result.confidence_notes)


def test_analyze_images_does_not_swallow_provider_failures() -> None:
    client = FailingVisionClient(VisionAPIError("Groq vision API returned 500: server error"))

    with pytest.raises(VisionAPIError):
        analyze_images([b"\xff\xd8\xfffake"], mode="room", client=client)
