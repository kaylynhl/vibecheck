"""Helpers for normalizing image inputs for multimodal analysis."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Sequence

from vibecheck.errors import InputNormalizationError
from vibecheck.schemas import ImageSource

MAX_IMAGE_COUNT = 5
DEFAULT_MAX_IMAGE_BYTES = 20 * 1024 * 1024

_SUFFIX_TO_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


def sniff_mime_type(data: bytes) -> str:
    """Best-effort MIME detection for raw image bytes."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"BM"):
        return "image/bmp"
    if data.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    return "image/jpeg"


def encode_image_as_data_url(image: ImageSource) -> str:
    """Encode an image input as a data URL for Groq multimodal requests."""
    encoded = base64.b64encode(image.data).decode("ascii")
    return f"data:{image.mime_type};base64,{encoded}"


def normalize_image_inputs(
    inputs: Sequence[str | Path | bytes],
    *,
    max_image_count: int = MAX_IMAGE_COUNT,
    max_image_bytes: int = DEFAULT_MAX_IMAGE_BYTES,
) -> list[ImageSource]:
    """Normalize local image paths or raw image bytes into ImageSource objects."""
    if not inputs:
        raise InputNormalizationError("At least one image input is required.")
    if len(inputs) > max_image_count:
        raise InputNormalizationError(
            f"Received {len(inputs)} images, but only up to {max_image_count} are supported."
        )

    normalized: list[ImageSource] = []
    for index, item in enumerate(inputs):
        if isinstance(item, (str, Path)):
            normalized.append(
                _normalize_path_input(
                    Path(item),
                    index=index,
                    max_image_bytes=max_image_bytes,
                )
            )
            continue
        if isinstance(item, bytes):
            normalized.append(
                _normalize_bytes_input(
                    item,
                    index=index,
                    max_image_bytes=max_image_bytes,
                )
            )
            continue
        raise InputNormalizationError(
            "Unsupported image input type. Expected str, Path, or bytes."
        )
    return normalized


def _normalize_path_input(
    path: Path,
    *,
    index: int,
    max_image_bytes: int,
) -> ImageSource:
    """Normalize a local image path into an ImageSource."""
    if not path.exists():
        raise InputNormalizationError(f"Image path does not exist: {path}")
    if not path.is_file():
        raise InputNormalizationError(f"Image path is not a file: {path}")

    try:
        data = path.read_bytes()
    except OSError as exc:
        raise InputNormalizationError(f"Unable to read image file: {path}") from exc

    if not data:
        raise InputNormalizationError(f"Image file is empty: {path}")
    if len(data) > max_image_bytes:
        raise InputNormalizationError(
            f"Image file exceeds the {max_image_bytes} byte limit: {path}"
        )

    mime_type = _SUFFIX_TO_MIME.get(path.suffix.lower(), sniff_mime_type(data))
    source_id = path.name or f"image_{index}"
    return ImageSource(
        source_id=source_id,
        mime_type=mime_type,
        data=data,
        origin=str(path),
    )


def _normalize_bytes_input(
    data: bytes,
    *,
    index: int,
    max_image_bytes: int,
) -> ImageSource:
    """Normalize raw image bytes into an ImageSource."""
    if not data:
        raise InputNormalizationError("Image bytes input cannot be empty.")
    if len(data) > max_image_bytes:
        raise InputNormalizationError(
            f"Image bytes at index {index} exceed the {max_image_bytes} byte limit."
        )

    mime_type = sniff_mime_type(data)
    return ImageSource(
        source_id=f"bytes_{index}",
        mime_type=mime_type,
        data=data,
        origin=f"bytes[{index}]",
    )
