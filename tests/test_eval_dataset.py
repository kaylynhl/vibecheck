"""Tests for the CLIP-LoRA evaluation helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_eval_dataset_counts_only_supported_images(tmp_path: Path) -> None:
    mod = _load_script("check_eval_dataset")
    cls_dir = tmp_path / "minimalist"
    cls_dir.mkdir()
    (cls_dir / "a.jpg").write_bytes(b"fake")
    (cls_dir / "b.HEIC").write_bytes(b"fake")
    (cls_dir / "notes.txt").write_text("not an image")

    counts = mod.count_images(tmp_path)

    assert counts["minimalist"] == 2
    assert counts["dark_academia"] == 0
    assert not mod.is_ready(counts, min_per_class=1)


def test_export_groq_baseline_uses_colab_portable_relative_keys(
    tmp_path: Path, monkeypatch
) -> None:
    mod = _load_script("export_groq_baseline")
    data_root = tmp_path / "eval"
    img = data_root / "minimalist" / "IMG_0001.jpg"
    img.parent.mkdir(parents=True)
    img.write_bytes(b"fake")
    monkeypatch.setattr(mod, "DATA_ROOT", data_root)

    assert mod.cache_key(img) == "minimalist/IMG_0001.jpg"


def test_export_groq_baseline_reads_older_absolute_cache_keys(
    tmp_path: Path, monkeypatch
) -> None:
    mod = _load_script("export_groq_baseline")
    data_root = tmp_path / "eval"
    img = data_root / "grunge" / "IMG_0042.jpg"
    img.parent.mkdir(parents=True)
    img.write_bytes(b"fake")
    monkeypatch.setattr(mod, "DATA_ROOT", data_root)

    cache = {str(img.resolve()): "grunge"}

    assert mod.cached_prediction(cache, img) == "grunge"


def test_export_groq_baseline_normalizes_legacy_cache_without_absolute_paths(
    tmp_path: Path, monkeypatch
) -> None:
    mod = _load_script("export_groq_baseline")
    data_root = tmp_path / "eval"
    img = data_root / "cottagecore" / "IMG_0003.jpg"
    stale_img = tmp_path / "old" / "minimalist" / "IMG_9999.jpg"
    img.parent.mkdir(parents=True)
    stale_img.parent.mkdir(parents=True)
    img.write_bytes(b"fake")
    stale_img.write_bytes(b"fake")
    monkeypatch.setattr(mod, "DATA_ROOT", data_root)

    cache = {
        str(img.resolve()): "cottagecore",
        str(stale_img.resolve()): "minimalist",
    }

    assert mod.normalize_cache(cache, [(img, "cottagecore")]) == {
        "cottagecore/IMG_0003.jpg": "cottagecore"
    }
