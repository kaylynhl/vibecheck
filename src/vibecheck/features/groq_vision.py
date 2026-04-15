"""Groq multimodal client for generating detailed visual scene descriptions."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Sequence

import requests

from vibecheck.errors import ConfigurationError, VisionAPIError, VisionOutputFormatError
from vibecheck.features.image_inputs import encode_image_as_data_url
from vibecheck.schemas import ImageSource, VisionAnalysisPayload

DEFAULT_GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"

VISION_SYSTEM_PROMPT = """You are a visual aesthetic analyst for room and outfit photos.
Your job is to produce grounded observations that help classify aesthetics and vibes.

Rules:
- Analyze only what is visibly supported by the images.
- Do not invent facts, brands, provenance, specific eras, materials, or intent unless they are visually justified.
- Keep direct observations separate from uncertain guesses.
- Prefer concrete, keyword-rich language useful for downstream vibe matching.
- If something is ambiguous, say so in the uncertainty fields instead of presenting it as fact.
- Output strict JSON only. No markdown, no code fences, no commentary outside the JSON object."""

VISION_USER_PROMPT_TEMPLATE = """Analyze all provided images together as one aesthetic-analysis request.
{mode_instruction}

Return exactly one JSON object with this shape:
{{
  "scene_type": "room | outfit | mixed | unclear",
  "visual_summary": "2-4 sentence grounded visual description.",
  "palette": ["short descriptive strings"],
  "lighting": ["short descriptive strings"],
  "textures": ["short descriptive strings"],
  "patterns": ["short descriptive strings"],
  "silhouette_or_shape": ["short descriptive strings"],
  "objects_or_items": ["short descriptive strings"],
  "mood_descriptors": ["short descriptive strings"],
  "aesthetic_descriptors": ["short descriptive strings"],
  "vibe_query": "comma-separated keywords and short phrases for vibe matching",
  "uncertainty_notes": ["short descriptive strings"],
  "observed_facts": ["short descriptive strings"],
  "uncertain_inferences": ["short descriptive strings"]
}}

Cover these dimensions in the JSON fields:
- color palette
- lighting
- materials and textures
- silhouette or shape language
- patterns
- clutter versus minimalism
- styling coherence
- mood
- era or cultural cues
- standout objects, decor, garments, or fashion pieces
- likely intended aesthetics
- possible ambiguities

Requirements:
- Keep the summary dense but grounded in what is visible.
- Use the vibe_query field as a compact search-style string of descriptive keywords and short phrases.
- Put uncertain guesses only in uncertainty_notes and uncertain_inferences.
- If the scene type is not clear, use "unclear"."""

_SCENE_TYPES = {"room", "outfit", "mixed", "unclear"}
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
    ) -> VisionAnalysisPayload:
        """Return a validated structured aesthetic analysis for the provided images."""
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
            raise VisionAPIError("Groq vision API returned an empty structured response.")
        return parse_vision_analysis_output(output_text.strip())

    def build_payload(
        self,
        images: Sequence[ImageSource],
        *,
        mode: str | None = None,
    ) -> dict[str, Any]:
        """Build the JSON payload for a Groq Responses API request."""
        system_prompt, user_prompt = build_vision_prompts(mode)

        user_content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": user_prompt,
            }
        ]
        for image in images:
            user_content.append(
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
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": user_content,
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


def build_vision_prompts(mode: str | None) -> tuple[str, str]:
    """Build the system and user prompts for the vision model."""
    mode_instruction = (
        f"The caller provided a mode hint: {mode}. Use it as context, but do not force the classification if the images disagree."
        if mode
        else "No mode hint was provided. Infer the scene type only from visible evidence."
    )
    return VISION_SYSTEM_PROMPT, VISION_USER_PROMPT_TEMPLATE.format(
        mode_instruction=mode_instruction
    )


def parse_vision_analysis_output(text: str) -> VisionAnalysisPayload:
    """Parse and strictly validate the structured JSON returned by the model."""
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise VisionOutputFormatError("Groq vision output was not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise VisionOutputFormatError("Groq vision output must be a top-level JSON object.")

    scene_type = _require_string(payload, "scene_type")
    if scene_type not in _SCENE_TYPES:
        raise VisionOutputFormatError(
            "Groq vision output contained an invalid scene_type."
        )

    visual_summary = _require_string(payload, "visual_summary")
    vibe_query = _require_string(payload, "vibe_query")

    return VisionAnalysisPayload(
        scene_type=scene_type,
        visual_summary=visual_summary,
        palette=_require_string_list(payload, "palette"),
        lighting=_require_string_list(payload, "lighting"),
        textures=_require_string_list(payload, "textures"),
        patterns=_require_string_list(payload, "patterns"),
        silhouette_or_shape=_require_string_list(payload, "silhouette_or_shape"),
        objects_or_items=_require_string_list(payload, "objects_or_items"),
        mood_descriptors=_require_string_list(payload, "mood_descriptors"),
        aesthetic_descriptors=_require_string_list(payload, "aesthetic_descriptors"),
        vibe_query=vibe_query,
        uncertainty_notes=_require_string_list(payload, "uncertainty_notes"),
        observed_facts=_require_string_list(payload, "observed_facts"),
        uncertain_inferences=_require_string_list(payload, "uncertain_inferences"),
    )


def compose_tag_extraction_text(payload: VisionAnalysisPayload) -> str:
    """Flatten the structured payload into keyword-rich text for tag extraction."""
    parts = [
        payload.visual_summary,
        ", ".join(payload.palette),
        ", ".join(payload.lighting),
        ", ".join(payload.textures),
        ", ".join(payload.patterns),
        ", ".join(payload.silhouette_or_shape),
        ", ".join(payload.objects_or_items),
        ", ".join(payload.mood_descriptors),
        ", ".join(payload.aesthetic_descriptors),
        payload.vibe_query,
        ", ".join(payload.observed_facts),
        ", ".join(payload.uncertain_inferences),
    ]
    return "\n".join(part.strip() for part in parts if part and part.strip())


def _require_string(payload: dict[str, Any], field: str) -> str:
    """Return a normalized required string field."""
    value = payload.get(field)
    if not isinstance(value, str):
        raise VisionOutputFormatError(
            f"Groq vision output field '{field}' must be a string."
        )
    normalized = value.strip()
    if not normalized:
        raise VisionOutputFormatError(
            f"Groq vision output field '{field}' cannot be empty."
        )
    return normalized


def _require_string_list(payload: dict[str, Any], field: str) -> list[str]:
    """Return a normalized required list[str] field."""
    value = payload.get(field)
    if not isinstance(value, list):
        raise VisionOutputFormatError(
            f"Groq vision output field '{field}' must be a list."
        )

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise VisionOutputFormatError(
                f"Groq vision output field '{field}' must contain only strings."
            )
        stripped = item.strip()
        if stripped:
            normalized.append(stripped)
    return normalized
