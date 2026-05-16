# CLIP-LoRA aesthetic classifier (production artifacts)

Trained in `notebooks/demo.ipynb` (Colab). Drop the contents of
`clip_lora_vibe.zip` (downloaded from the notebook's §9.1 cell) here.

Expected layout after extraction:

```
models/clip_lora/
  lora_adapters/
    adapter_config.json
    adapter_model.safetensors
  classifier.pt
  classes.json
```

The runtime classifier (`src/vibecheck/vibe/clip_lora.py`) and the
pipeline pick these up automatically. If any file is missing, the
pipeline falls back to the text-based vibe scorers and surfaces a
warning in the response.

Total size: ~3 MB (LoRA adapters are tiny relative to the 150 MB
CLIP-ViT-B/32 backbone, which `transformers` pulls from HuggingFace at
first use and caches under `~/.cache/huggingface/`).
