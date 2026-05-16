"""CLIP-LoRA aesthetic classifier wired into the vibecheck pipeline.

Loads the LoRA adapters and linear classification head trained in
``notebooks/demo.ipynb`` and exposes a ``predict_vibe_scores`` API that
returns the same ``VibeScore`` shape the rest of the pipeline expects.

The CLIP backbone is fetched from HuggingFace at first use; only the
small (~1 MB) LoRA adapter weights and the linear head live in the repo
under ``models/clip_lora/``.
"""

from __future__ import annotations

import io
import json
import threading
from pathlib import Path
from typing import Sequence

from PIL import Image

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

from vibecheck.errors import ConfigurationError
from vibecheck.schemas import VibeScore

CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
DEFAULT_ARTIFACTS_DIR = (
    Path(__file__).resolve().parents[3] / "models" / "clip_lora"
)

_load_lock = threading.Lock()


class CLIPLoRAVibeClassifier:
    """Lazy-loaded CLIP-LoRA classifier over the trained aesthetic taxonomy."""

    def __init__(self, artifacts_dir: Path | None = None) -> None:
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else DEFAULT_ARTIFACTS_DIR
        self._loaded = False
        self._device: str | None = None
        self._classes: list[str] | None = None
        self._processor = None
        self._vision = None
        self._visual_projection = None
        self._classifier = None

    @property
    def is_available(self) -> bool:
        d = self.artifacts_dir
        return (
            d.exists()
            and (d / "lora_adapters").is_dir()
            and (d / "classifier.pt").is_file()
            and (d / "classes.json").is_file()
        )

    @property
    def classes(self) -> list[str]:
        self._ensure_loaded()
        return list(self._classes or [])

    def _ensure_loaded(self) -> None:
        with _load_lock:
            if self._loaded:
                return
            if not self.is_available:
                raise ConfigurationError(
                    f"CLIP-LoRA artifacts not found under {self.artifacts_dir}. "
                    "Train the model in notebooks/demo.ipynb (Colab) and unzip "
                    "the downloaded artifacts into that directory."
                )

            import torch
            import torch.nn as nn
            from peft import PeftModel
            from transformers import CLIPModel, CLIPProcessor

            self._device = (
                "cuda"
                if torch.cuda.is_available()
                else "mps"
                if hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
                else "cpu"
            )

            base = CLIPModel.from_pretrained(CLIP_MODEL_NAME)
            vision = PeftModel.from_pretrained(
                base.vision_model, str(self.artifacts_dir / "lora_adapters")
            )
            self._classes = json.loads(
                (self.artifacts_dir / "classes.json").read_text()
            )
            classifier = nn.Linear(base.config.projection_dim, len(self._classes))
            state = torch.load(
                self.artifacts_dir / "classifier.pt",
                map_location=self._device,
            )
            classifier.load_state_dict(state)

            self._processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)
            self._vision = vision.eval().to(self._device)
            self._visual_projection = base.visual_projection.eval().to(self._device)
            self._classifier = classifier.eval().to(self._device)
            self._loaded = True

    def predict_probs(
        self, images: Sequence[bytes | Image.Image | str | Path]
    ) -> list[dict[str, float]]:
        """Return per-image probability distributions over the trained classes."""
        import torch
        import torch.nn.functional as F

        self._ensure_loaded()
        if not images:
            return []

        pil_images: list[Image.Image] = []
        for img in images:
            if isinstance(img, (bytes, bytearray)):
                pil_images.append(Image.open(io.BytesIO(img)).convert("RGB"))
            elif isinstance(img, (str, Path)):
                pil_images.append(Image.open(img).convert("RGB"))
            else:
                pil_images.append(img.convert("RGB"))

        with torch.no_grad():
            inputs = self._processor(images=pil_images, return_tensors="pt").to(self._device)
            v = self._vision(**inputs).pooler_output
            v = self._visual_projection(v)
            logits = self._classifier(v)
            probs = F.softmax(logits, dim=-1).cpu().numpy()

        return [
            {cls: float(p) for cls, p in zip(self._classes or [], row)}
            for row in probs
        ]

    def predict_vibe_scores(
        self,
        images: Sequence[bytes | Image.Image | str | Path],
        *,
        top_k: int | None = None,
    ) -> list[VibeScore]:
        """Average per-image probabilities into a single ranked vibe list."""
        per_image = self.predict_probs(images)
        if not per_image:
            return []

        n = len(per_image)
        avg = {cls: sum(p[cls] for p in per_image) / n for cls in per_image[0]}
        ranked = sorted(avg.items(), key=lambda kv: kv[1], reverse=True)
        if top_k is not None:
            ranked = ranked[:top_k]

        n_classes = len(self._classes or [])
        return [
            VibeScore(
                vibe=cls,
                score=float(score),
                matched_keywords=[],
                description=(
                    f"CLIP-LoRA prediction (rank-8 adapters on CLIP-ViT-B/32, "
                    f"trained over {n_classes} aesthetic classes)"
                ),
            )
            for cls, score in ranked
        ]


_singleton: CLIPLoRAVibeClassifier | None = None


def get_default_classifier() -> CLIPLoRAVibeClassifier:
    """Return a process-wide singleton classifier."""
    global _singleton
    if _singleton is None:
        _singleton = CLIPLoRAVibeClassifier()
    return _singleton
