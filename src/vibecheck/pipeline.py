"""Top-level orchestration for the core image-to-vibe analysis pipeline."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Literal, Sequence

from vibecheck.errors import VisionOutputFormatError
from vibecheck.features.groq_vision import (
    GroqVisionClient,
    compose_tag_extraction_text,
)
from vibecheck.features.image_inputs import normalize_image_inputs
from vibecheck.schemas import DebugInfo, VibeAnalysisResult
from vibecheck.tags.extract import extract_structured_tags
from vibecheck.vibe.scoring import score_vibes

Mode = Literal["room", "outfit"]


def analyze_images(
    inputs: Sequence[str | Path | bytes],
    *,
    mode: Mode | None = None,
    client: GroqVisionClient | None = None,
) -> VibeAnalysisResult:
    """Run the full image-to-vibe pipeline and return a structured analysis result."""
    timings_ms: dict[str, int] = {}
    warnings: list[str] = []

    start = perf_counter()
    normalized_inputs = normalize_image_inputs(inputs)
    timings_ms["normalize_inputs"] = _elapsed_ms(start)

    vision_client = client or GroqVisionClient()

    raw_description = ""
    extracted_tags = []
    validation_passed = True
    parse_error: str | None = None
    scene_type: str | None = None

    start = perf_counter()
    try:
        vision_payload = vision_client.analyze_images(normalized_inputs, mode=mode)
        raw_description = vision_payload.visual_summary
        scene_type = vision_payload.scene_type
    except VisionOutputFormatError as exc:
        validation_passed = False
        parse_error = str(exc)
        warnings.append(
            "Vision model output could not be parsed into the required structured JSON."
        )
        confidence_notes = [
            "Vision output was malformed or invalid, so rankings are low-confidence."
        ]
        timings_ms["vision_description"] = _elapsed_ms(start)

        start = perf_counter()
        vibe_scores, score_notes = score_vibes(extracted_tags, mode=mode)
        timings_ms["score_vibes"] = _elapsed_ms(start)
        confidence_notes.extend(score_notes)

        top_vibes = vibe_scores[:3]
        debug = DebugInfo(
            input_count=len(normalized_inputs),
            input_kinds=[image.mime_type for image in normalized_inputs],
            model=vision_client.model or "",
            timings_ms=timings_ms,
            warnings=warnings,
            scene_type=scene_type,
            validation_passed=validation_passed,
            parse_error=parse_error,
        )
        return VibeAnalysisResult(
            raw_description=raw_description,
            extracted_tags=extracted_tags,
            vibe_scores=vibe_scores,
            top_vibes=top_vibes,
            confidence_notes=confidence_notes,
            debug=debug,
        )
    timings_ms["vision_description"] = _elapsed_ms(start)

    start = perf_counter()
    extracted_tags = extract_structured_tags(compose_tag_extraction_text(vision_payload))
    timings_ms["extract_tags"] = _elapsed_ms(start)

    start = perf_counter()
    vibe_scores, confidence_notes = score_vibes(extracted_tags, mode=mode)
    timings_ms["score_vibes"] = _elapsed_ms(start)

    if mode and scene_type and scene_type not in {mode, "mixed", "unclear"}:
        warnings.append(
            f"Scene type '{scene_type}' did not match the requested mode '{mode}'."
        )
        confidence_notes = [
            f"Detected scene type '{scene_type}' may not align with the requested mode '{mode}'."
        ] + confidence_notes

    if vision_payload.uncertainty_notes:
        confidence_notes.extend(vision_payload.uncertainty_notes)

    if not extracted_tags:
        warnings.append(
            "No normalized tags were extracted from the raw description."
        )
        confidence_notes = [
            "No normalized tags were extracted from the raw description; rankings are low-confidence."
        ] + confidence_notes

    top_vibes = [score for score in vibe_scores if score.score > 0][:3]
    if not top_vibes and vibe_scores:
        warnings.append("No positive vibe scores were found; returning the ranked list for inspection.")
        top_vibes = vibe_scores[:3]

    debug = DebugInfo(
        input_count=len(normalized_inputs),
        input_kinds=[image.mime_type for image in normalized_inputs],
        model=vision_client.model or "",
        timings_ms=timings_ms,
        warnings=warnings,
        scene_type=scene_type,
        validation_passed=validation_passed,
        parse_error=parse_error,
    )
    return VibeAnalysisResult(
        raw_description=raw_description,
        extracted_tags=extracted_tags,
        vibe_scores=vibe_scores,
        top_vibes=top_vibes,
        confidence_notes=confidence_notes,
        debug=debug,
    )


def analyze_images_to_dict(
    inputs: Sequence[str | Path | bytes],
    *,
    mode: Mode | None = None,
    client: GroqVisionClient | None = None,
) -> dict[str, object]:
    """Run the pipeline and return a JSON-ready dictionary."""
    return analyze_images(inputs, mode=mode, client=client).to_dict()


def _elapsed_ms(start_time: float) -> int:
    """Convert elapsed perf-counter time into integer milliseconds."""
    return int((perf_counter() - start_time) * 1000)
