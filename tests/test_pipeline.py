from __future__ import annotations

import pytest

from vibecheck.errors import VisionAPIError
from vibecheck.pipeline import analyze_images, analyze_images_to_dict
from helpers import FailingVisionClient, StubVisionClient, make_payload


def test_analyze_images_end_to_end(room_payload) -> None:
    client = StubVisionClient(room_payload)

    result = analyze_images([b"\xff\xd8\xfffake"], mode="room", client=client)

    assert result.raw_description
    assert result.extracted_tags
    assert result.vibe_scores
    assert result.top_vibes
    assert result.debug.model == "stub-model"


def test_analyze_images_to_dict_returns_json_ready_shape(outfit_payload) -> None:
    client = StubVisionClient(outfit_payload)

    result = analyze_images_to_dict([b"\xff\xd8\xfffake"], mode="outfit", client=client)

    assert set(result.keys()) == {
        "raw_description",
        "extracted_tags",
        "vibe_scores",
        "top_vibes",
        "confidence_notes",
        "debug",
        "item_recommendations",
        "playlist_recommendations",
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
    assert any(
        "No normalized tags were extracted" in note for note in result.confidence_notes
    )
    assert any(
        "No normalized tags were extracted" in warning
        for warning in result.debug.warnings
    )


def test_analyze_images_uses_vibe_query_and_structured_fields_for_tag_extraction() -> (
    None
):
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

    assert {tag.value for tag in result.extracted_tags} >= {
        "cream",
        "smooth",
        "solid",
        "fitted",
    }


def test_analyze_images_adds_scene_mode_mismatch_note(room_payload) -> None:
    client = StubVisionClient(room_payload)

    result = analyze_images([b"\xff\xd8\xfffake"], mode="outfit", client=client)

    assert any("requested mode" in note for note in result.confidence_notes)
    assert any("did not match" in warning for warning in result.debug.warnings)


def test_analyze_images_handles_malformed_vision_output_gracefully(
    malformed_output_error,
) -> None:
    client = FailingVisionClient(malformed_output_error)

    result = analyze_images([b"\xff\xd8\xfffake"], mode="room", client=client)

    assert result.raw_description == ""
    assert result.extracted_tags == []
    assert result.vibe_scores
    assert result.top_vibes
    assert result.debug.validation_passed is False
    assert result.debug.parse_error == "Groq vision output was not valid JSON."
    assert any("malformed or invalid" in note for note in result.confidence_notes)


def test_analyze_images_does_not_swallow_provider_failures(
    provider_failure_error,
) -> None:
    client = FailingVisionClient(provider_failure_error)

    with pytest.raises(VisionAPIError):
        analyze_images([b"\xff\xd8\xfffake"], mode="room", client=client)


def test_analyze_images_supports_multi_image_requests(room_payload) -> None:
    client = StubVisionClient(room_payload)

    result = analyze_images(
        [b"\xff\xd8\xfffirst", b"\xff\xd8\xffsecond"],
        mode="room",
        client=client,
    )

    assert result.top_vibes
    assert len(client.calls) == 1
    assert len(client.calls[0]["images"]) == 2
    assert client.calls[0]["mode"] == "room"
