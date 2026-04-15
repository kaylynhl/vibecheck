"""Deterministic extraction of normalized tags from a vision description."""

from __future__ import annotations

import re
from collections.abc import Iterable

from vibecheck.errors import TagExtractionError
from vibecheck.schemas import ExtractedTag
from vibecheck.tags.vocabulary import INFERRED_HINTS, TAG_VOCABULARY


def extract_structured_tags(description: str) -> list[ExtractedTag]:
    """Extract normalized visual tags from a natural-language description."""
    if not description or not description.strip():
        raise TagExtractionError("A non-empty raw description is required.")

    normalized = _normalize_text(description)
    matches: dict[tuple[str, str], ExtractedTag] = {}

    for category, values in TAG_VOCABULARY.items():
        for canonical, phrases in values.items():
            direct_evidence = _find_phrase_match(normalized, (canonical,))
            if direct_evidence:
                _store_match(
                    matches,
                    ExtractedTag(
                        category=category,
                        value=canonical,
                        confidence=0.95,
                        evidence=direct_evidence,
                    ),
                )
                continue

            synonym_evidence = _find_phrase_match(normalized, phrases)
            if synonym_evidence:
                _store_match(
                    matches,
                    ExtractedTag(
                        category=category,
                        value=canonical,
                        confidence=0.82,
                        evidence=synonym_evidence,
                    ),
                )

    for category, canonical, phrase in INFERRED_HINTS:
        inferred_evidence = _find_phrase_match(normalized, (phrase,))
        if inferred_evidence:
            _store_match(
                matches,
                ExtractedTag(
                    category=category,
                    value=canonical,
                    confidence=0.67,
                    evidence=inferred_evidence,
                ),
            )

    extracted = sorted(
        matches.values(),
        key=lambda tag: (-tag.confidence, tag.category, tag.value),
    )
    return extracted


def _normalize_text(text: str) -> str:
    """Lowercase and collapse whitespace for deterministic phrase matching."""
    lowered = text.lower().replace("/", " ")
    lowered = re.sub(r"[^a-z0-9\s\-]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _find_phrase_match(text: str, phrases: Iterable[str]) -> str | None:
    """Return the first matched phrase from the provided candidates."""
    for phrase in phrases:
        pattern = rf"(?<!\w){re.escape(phrase.lower())}(?!\w)"
        if re.search(pattern, text):
            return phrase
    return None


def _store_match(matches: dict[tuple[str, str], ExtractedTag], tag: ExtractedTag) -> None:
    """Keep the highest-confidence match for each (category, value) pair."""
    key = (tag.category, tag.value)
    existing = matches.get(key)
    if existing is None or tag.confidence > existing.confidence:
        matches[key] = tag
