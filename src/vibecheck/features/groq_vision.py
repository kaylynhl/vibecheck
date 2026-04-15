"""Groq multimodal client for generating detailed visual scene descriptions."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Sequence

import requests

from vibecheck.errors import ConfigurationError, VisionAPIError
from vibecheck.features.image_inputs import encode_image_as_data_url
from vibecheck.schemas import ImageSource

DEFAULT_GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"

_ANALYSIS_PROMPT = """You are a visual style analyst for an aesthetic recommendation system.
Analyze all provided images together as one request. Produce a dense natural-language description
that captures the overall vibe and the important visual evidence. Cover:
- setting and whether this appears to be a room or outfit
- main color palette and contrast
- lighting quality and mood
- materials and textures
- patterns and silhouette/shape cues
- notable furniture, decor, garments, accessories, or styling choices
- how cohesive or mixed the visuals feel
- any uncertainty or ambiguity

Write clearly and concretely. Do not output JSON. Do not recommend products or music."""


@dataclass
class GroqVisionClient:
    """Thin client for Groq's OpenAI-compatible Responses API."""

    api_key: str | None = None
    model: str | None = None
    base_url: str = DEFAULT_GROQ_BASE_URL
    timeout_seconds: int = 60
    session: requests.Session | None = None

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ConfigurationError(
                "GROQ_API_KEY is required to call the Groq vision API."
            )
        self.model = self.model or os.getenv(
            "GROQ_VISION_MODEL", DEFAULT_GROQ_VISION_MODEL
        )
        self.session = self.session or requests.Session()

    def analyze_images(
        self,
        images: Sequence[ImageSource],
        *,
        mode: str | None = None,
    ) -> str:
        """Return a detailed natural-language description for the provided images."""
        payload = self.build_payload(images, mode=mode)
        url = f"{self.base_url.rstrip('/')}/responses"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise VisionAPIError("Failed to connect to the Groq vision API.") from exc

        if response.status_code >= 400:
            raise VisionAPIError(
                f"Groq vision API returned {response.status_code}: {response.text}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise VisionAPIError("Groq vision API returned invalid JSON.") from exc

        output_text = self.extract_output_text(body)
        if not output_text.strip():
            raise VisionAPIError("Groq vision API returned an empty description.")
        return output_text.strip()

    def build_payload(
        self,
        images: Sequence[ImageSource],
        *,
        mode: str | None = None,
    ) -> dict[str, Any]:
        """Build the JSON payload for a Groq Responses API request."""
        prompt = _ANALYSIS_PROMPT
        if mode:
            prompt = f"{prompt}\n\nThe caller expects analysis for mode: {mode}."

        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": prompt,
            }
        ]
        for image in images:
            content.append(
                {
                    "type": "input_image",
                    "detail": "auto",
                    "image_url": encode_image_as_data_url(image),
                }
            )

        return {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
        }

    @staticmethod
    def extract_output_text(body: dict[str, Any]) -> str:
        """Extract output text from Groq's Responses API response body."""
        output_text = body.get("output_text")
        if isinstance(output_text, str):
            return output_text

        fragments: list[str] = []
        for item in body.get("output", []):
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if not isinstance(content, dict):
                    continue
                text_value = content.get("text")
                if isinstance(text_value, str):
                    fragments.append(text_value)
        return "\n".join(fragment for fragment in fragments if fragment)
