from __future__ import annotations

from pathlib import Path

import pytest

from vibecheck.errors import InputNormalizationError
from vibecheck.features.image_inputs import (
    MAX_IMAGE_COUNT,
    encode_image_as_data_url,
    normalize_image_inputs,
    sniff_mime_type,
)


def test_normalize_path_input(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nrest")

    result = normalize_image_inputs([image_path])

    assert len(result) == 1
    assert result[0].mime_type == "image/png"
    assert result[0].origin == str(image_path)


def test_normalize_bytes_input_uses_sniffed_mime_type() -> None:
    result = normalize_image_inputs([b"\xff\xd8\xfftest"])

    assert result[0].mime_type == "image/jpeg"
    assert result[0].origin == "bytes[0]"


def test_sniff_mime_type_defaults_to_jpeg() -> None:
    assert sniff_mime_type(b"not-a-known-signature") == "image/jpeg"


def test_encode_data_url_contains_mime_and_payload() -> None:
    image = normalize_image_inputs([b"\xff\xd8\xfftest"])[0]

    assert encode_image_as_data_url(image).startswith("data:image/jpeg;base64,")


def test_normalize_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(InputNormalizationError):
        normalize_image_inputs([tmp_path / "missing.png"])


def test_normalize_rejects_empty_inputs() -> None:
    with pytest.raises(InputNormalizationError):
        normalize_image_inputs([])


def test_normalize_rejects_unsupported_type() -> None:
    with pytest.raises(InputNormalizationError):
        normalize_image_inputs([123])  # type: ignore[list-item]


def test_normalize_rejects_too_many_images() -> None:
    with pytest.raises(InputNormalizationError):
        normalize_image_inputs([b"\xff\xd8\xff"] * (MAX_IMAGE_COUNT + 1))
