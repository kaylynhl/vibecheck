from __future__ import annotations

import json
import requests

import pytest

from vibecheck.errors import (
    ConfigurationError,
    VisionAPIError,
    VisionOutputFormatError,
)
from vibecheck.features.groq_vision import (
    GroqVisionClient,
    build_vision_prompts,
    compose_tag_extraction_text,
    parse_vision_analysis_output,
)
from vibecheck.features.image_inputs import normalize_image_inputs


class DummyResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload


class DummySession:
    def __init__(self, response: DummyResponse | Exception) -> None:
        self.response = response
        self.last_request = None

    def post(self, url: str, json: dict, headers: dict, timeout: int) -> DummyResponse:
        self.last_request = {
            "url": url,
            "json": json,
            "headers": headers,
            "timeout": timeout,
        }
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_client_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ConfigurationError):
        GroqVisionClient(api_key=None, session=DummySession(DummyResponse(200)))


def test_build_payload_includes_input_images() -> None:
    images = normalize_image_inputs([b"\xff\xd8\xfffake"])
    client = GroqVisionClient(api_key="test-key", session=DummySession(DummyResponse(200)))

    payload = client.build_payload(images, mode="room")

    assert payload["model"] == client.model
    assert payload["input"][0]["role"] == "system"
    assert payload["input"][1]["role"] == "user"
    content = payload["input"][1]["content"]
    assert content[0]["type"] == "input_text"
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/jpeg;base64,")

    # Schema-enforced JSON output: the decoder is constrained to produce
    # output matching `vibe_analysis_output`. Without this, Llama-4 Scout
    # produced malformed JSON on a large fraction of arbitrary photos.
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["name"] == "vibe_analysis_output"
    schema = payload["text"]["format"]["schema"]
    assert schema["type"] == "object"
    assert "scene_type" in schema["properties"]
    assert "vibe_query" in schema["properties"]
    assert schema["additionalProperties"] is False


def test_analyze_images_wraps_http_errors() -> None:
    client = GroqVisionClient(
        api_key="test-key",
        session=DummySession(requests.RequestException("boom")),
    )

    with pytest.raises(VisionAPIError):
        client.analyze_images(normalize_image_inputs([b"\xff\xd8\xfffake"]))


def test_analyze_images_wraps_error_status() -> None:
    client = GroqVisionClient(
        api_key="test-key",
        session=DummySession(DummyResponse(500, text="server error")),
    )

    with pytest.raises(VisionAPIError):
        client.analyze_images(normalize_image_inputs([b"\xff\xd8\xfffake"]))


def test_analyze_images_returns_structured_payload(room_payload) -> None:
    client = GroqVisionClient(
        api_key="test-key",
        session=DummySession(
            DummyResponse(
                200,
                payload={
                    "output_text": json.dumps(room_payload.to_dict())
                },
            )
        ),
    )

    payload = client.analyze_images(normalize_image_inputs([b"\xff\xd8\xfffake"]))

    assert payload.scene_type == "room"
    assert payload.visual_summary == room_payload.visual_summary


def test_parse_vision_analysis_output_accepts_representative_room_json(room_payload) -> None:
    payload = parse_vision_analysis_output(json.dumps(room_payload.to_dict()))

    assert payload.scene_type == "room"
    assert "warm neutrals" in payload.palette


def test_parse_vision_analysis_output_accepts_representative_outfit_json(outfit_payload) -> None:
    payload = parse_vision_analysis_output(json.dumps(outfit_payload.to_dict()))

    assert payload.scene_type == "outfit"
    assert "fitted" in payload.silhouette_or_shape


def test_build_vision_prompts_include_required_instructions() -> None:
    system_prompt, user_prompt = build_vision_prompts("outfit")

    assert "JSON schema" in system_prompt
    assert "do not invent facts" in system_prompt.lower()
    assert "vibe_query" in user_prompt
    assert "color palette" in user_prompt


def test_parse_vision_analysis_output_rejects_missing_field() -> None:
    with pytest.raises(VisionOutputFormatError):
        parse_vision_analysis_output('{"scene_type":"room"}')


def test_parse_vision_analysis_output_rejects_wrong_type() -> None:
    with pytest.raises(VisionOutputFormatError):
        parse_vision_analysis_output(
            """{
              "scene_type": "room",
              "visual_summary": "Summary",
              "palette": "warm neutrals",
              "lighting": [],
              "textures": [],
              "patterns": [],
              "silhouette_or_shape": [],
              "objects_or_items": [],
              "mood_descriptors": [],
              "aesthetic_descriptors": [],
              "vibe_query": "query",
              "uncertainty_notes": [],
              "observed_facts": [],
              "uncertain_inferences": []
            }"""
        )


def test_parse_vision_analysis_output_rejects_invalid_scene_type() -> None:
    with pytest.raises(VisionOutputFormatError):
        parse_vision_analysis_output(
            """{
              "scene_type": "landscape",
              "visual_summary": "Summary",
              "palette": [],
              "lighting": [],
              "textures": [],
              "patterns": [],
              "silhouette_or_shape": [],
              "objects_or_items": [],
              "mood_descriptors": [],
              "aesthetic_descriptors": [],
              "vibe_query": "query",
              "uncertainty_notes": [],
              "observed_facts": [],
              "uncertain_inferences": []
            }"""
        )


def test_parse_vision_analysis_output_rejects_non_json_text() -> None:
    with pytest.raises(VisionOutputFormatError):
        parse_vision_analysis_output("not json")


def test_compose_tag_extraction_text_uses_structured_fields() -> None:
    payload = parse_vision_analysis_output(
        """{
          "scene_type": "outfit",
          "visual_summary": "A fitted outfit in cream tones.",
          "palette": ["cream"],
          "lighting": ["bright natural"],
          "textures": ["smooth"],
          "patterns": ["solid"],
          "silhouette_or_shape": ["fitted"],
          "objects_or_items": ["structured blazer"],
          "mood_descriptors": ["polished"],
          "aesthetic_descriptors": ["clean girl"],
          "vibe_query": "cream, fitted silhouette, polished minimal outfit",
          "uncertainty_notes": [],
          "observed_facts": ["light neutral palette"],
          "uncertain_inferences": []
        }"""
    )

    text = compose_tag_extraction_text(payload)

    assert "cream" in text
    assert "fitted" in text
    assert "vibe_query" not in text
