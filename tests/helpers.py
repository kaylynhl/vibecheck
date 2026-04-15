from __future__ import annotations

from vibecheck.schemas import VisionAnalysisPayload


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
    """Build a reusable structured vision payload for tests."""
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


class StubVisionClient:
    """Mocked vision client that returns a fixed payload and tracks calls."""

    def __init__(self, payload: VisionAnalysisPayload, model: str = "stub-model") -> None:
        self.payload = payload
        self.model = model
        self.calls = []

    def analyze_images(self, images, *, mode=None) -> VisionAnalysisPayload:
        self.calls.append({"images": images, "mode": mode})
        return self.payload


class FailingVisionClient:
    """Mocked vision client that raises a configured error."""

    def __init__(self, error: Exception, model: str = "stub-model") -> None:
        self.error = error
        self.model = model

    def analyze_images(self, images, *, mode=None) -> VisionAnalysisPayload:
        raise self.error
