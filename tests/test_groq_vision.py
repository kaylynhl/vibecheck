from __future__ import annotations

import requests

import pytest

from vibecheck.errors import ConfigurationError, VisionAPIError
from vibecheck.features.groq_vision import GroqVisionClient
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
    content = payload["input"][0]["content"]
    assert content[0]["type"] == "input_text"
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/jpeg;base64,")


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


def test_analyze_images_returns_output_text() -> None:
    client = GroqVisionClient(
        api_key="test-key",
        session=DummySession(DummyResponse(200, payload={"output_text": "Detailed description"})),
    )

    description = client.analyze_images(normalize_image_inputs([b"\xff\xd8\xfffake"]))

    assert description == "Detailed description"
