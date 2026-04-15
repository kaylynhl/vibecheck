from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibecheck.errors import VisionAPIError, VisionOutputFormatError
from vibecheck.schemas import VisionAnalysisPayload
from helpers import make_payload


@pytest.fixture
def room_payload() -> VisionAnalysisPayload:
    """Canonical mocked room payload for tests."""
    return make_payload(
        scene_type="room",
        visual_summary="A cozy room with warm neutrals, wood furniture, and woven textures.",
        palette=["warm neutrals"],
        lighting=["natural"],
        textures=["woven", "cozy"],
        patterns=["floral"],
        objects_or_items=["wood furniture"],
        mood_descriptors=["cozy"],
        aesthetic_descriptors=["cottagecore"],
        vibe_query="warm neutrals, natural light, woven textures, floral, wood furniture",
        uncertainty_notes=["Some corners are partially obscured."],
        observed_facts=["wood furniture", "soft natural lighting"],
        uncertain_inferences=["possibly vintage-inspired"],
    )


@pytest.fixture
def outfit_payload() -> VisionAnalysisPayload:
    """Canonical mocked outfit payload for tests."""
    return make_payload(
        scene_type="outfit",
        visual_summary="A sleek fitted outfit with cream tones and smooth fabric.",
        palette=["cream"],
        lighting=["natural"],
        textures=["smooth"],
        patterns=["solid"],
        silhouette_or_shape=["fitted"],
        objects_or_items=["structured blazer"],
        mood_descriptors=["polished"],
        aesthetic_descriptors=["clean girl"],
        vibe_query="cream, smooth fabric, fitted silhouette, polished minimal outfit",
        observed_facts=["light neutral palette"],
    )


@pytest.fixture
def malformed_output_error() -> VisionOutputFormatError:
    """Canonical structured-output parse failure for fallback tests."""
    return VisionOutputFormatError("Groq vision output was not valid JSON.")


@pytest.fixture
def provider_failure_error() -> VisionAPIError:
    """Canonical provider failure for non-fallback tests."""
    return VisionAPIError("Groq vision API returned 500: server error")
