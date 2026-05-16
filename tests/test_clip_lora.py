"""Tests for the CLIP-LoRA runtime classifier.

These run without the heavy torch/transformers stack — they exercise the
availability check and the missing-artifact failure path. End-to-end
inference is exercised manually after the model is downloaded.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vibecheck.errors import ConfigurationError
from vibecheck.vibe.clip_lora import (
    DEFAULT_ARTIFACTS_DIR,
    CLIPLoRAVibeClassifier,
)


def test_is_available_false_when_dir_missing(tmp_path: Path) -> None:
    clf = CLIPLoRAVibeClassifier(artifacts_dir=tmp_path / "nope")
    assert clf.is_available is False


def test_is_available_false_when_partial(tmp_path: Path) -> None:
    (tmp_path / "lora_adapters").mkdir()
    (tmp_path / "classes.json").write_text("[]")
    # classifier.pt missing
    clf = CLIPLoRAVibeClassifier(artifacts_dir=tmp_path)
    assert clf.is_available is False


def test_predict_raises_without_artifacts(tmp_path: Path) -> None:
    clf = CLIPLoRAVibeClassifier(artifacts_dir=tmp_path / "nope")
    with pytest.raises(ConfigurationError):
        clf.predict_probs([b"\x89PNG\r\n\x1a\n"])


def test_default_artifacts_dir_resolves_to_repo_root() -> None:
    assert DEFAULT_ARTIFACTS_DIR.name == "clip_lora"
    assert DEFAULT_ARTIFACTS_DIR.parent.name == "models"
