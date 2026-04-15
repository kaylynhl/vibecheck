"""Dataclasses for the core vibe analysis pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ImageSource:
    """Normalized image input ready for downstream processing."""

    source_id: str
    mime_type: str
    data: bytes
    origin: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation without raw bytes."""
        return {
            "source_id": self.source_id,
            "mime_type": self.mime_type,
            "origin": self.origin,
            "byte_length": len(self.data),
        }


@dataclass
class ExtractedTag:
    """Structured visual attribute extracted from the image description."""

    category: str
    value: str
    confidence: float
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation of the extracted tag."""
        return asdict(self)


@dataclass
class VibeScore:
    """Weighted vibe score derived from the extracted tags."""

    vibe: str
    score: float
    matched_keywords: list[str]
    description: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation of the score."""
        return asdict(self)


@dataclass
class DebugInfo:
    """Internal pipeline metadata useful for debugging and inspection."""

    input_count: int
    input_kinds: list[str]
    model: str
    timings_ms: dict[str, int]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation of the debug information."""
        return asdict(self)


@dataclass
class VibeAnalysisResult:
    """Structured result returned by the image-to-vibe pipeline."""

    raw_description: str
    extracted_tags: list[ExtractedTag]
    vibe_scores: list[VibeScore]
    top_vibes: list[VibeScore]
    confidence_notes: list[str]
    debug: DebugInfo

    def to_dict(self) -> dict[str, Any]:
        """Return a fully JSON-safe representation of the analysis result."""
        return {
            "raw_description": self.raw_description,
            "extracted_tags": [tag.to_dict() for tag in self.extracted_tags],
            "vibe_scores": [score.to_dict() for score in self.vibe_scores],
            "top_vibes": [score.to_dict() for score in self.top_vibes],
            "confidence_notes": list(self.confidence_notes),
            "debug": self.debug.to_dict(),
        }
