# Labeled aesthetic dataset

This directory holds the labeled photo corpus used to train and evaluate
the CLIP-LoRA aesthetic classifier (see `notebooks/demo.ipynb`). The same
held-out test split is used to compare four systems:

1. Groq Vision (Llama-4 Scout, current production baseline)
2. CLIP-ViT-B/32 zero-shot (prompted, no training)
3. CLIP-ViT-B/32 linear probe (trained head, frozen backbone)
4. CLIP-ViT-B/32 + LoRA (rank-8 adapters fine-tuned on the vision tower)

## Folder = label

Each photo's label is its parent directory name. The current corpus has
**430 photos across 18 aesthetic classes**, with each class capped at 40
photos and a floor of 8 (anything sparser was dropped to keep stratified
splits viable).

| Folder                 | Photos | Aesthetic            |
| ---------------------- | ------ | -------------------- |
| `bohemian/`            | 8      | bohemian             |
| `coastal_grandmother/` | 40     | coastal grandmother  |
| `coquette/`            | 40     | coquette             |
| `cottagecore/`         | 40     | cottagecore          |
| `dark_academia/`       | 11     | dark academia        |
| `grunge/`              | 37     | grunge               |
| `indie_folk/`          | 11     | indie folk           |
| `indie_sleaze/`        | 19     | indie sleaze         |
| `lo_fi/`               | 12     | lo-fi                |
| `mid_century_modern/`  | 22     | mid-century modern   |
| `minimalist/`          | 40     | minimalist           |
| `normcore/`            | 40     | normcore             |
| `old_money/`           | 40     | old money            |
| `quiet_luxury/`        | 18     | quiet luxury         |
| `retro_70s/`           | 9      | retro 70s            |
| `scandinavian/`        | 12     | scandinavian         |
| `soft_girl/`           | 14     | soft girl            |
| `twee/`                | 17     | twee                 |

## Readiness check

Before opening the Colab notebook, you can verify the dataset is intact:

```bash
python scripts/check_eval_dataset.py
```

The default gate is 8 photos per class. To cache the production Groq
baseline once the check passes:

```bash
python scripts/export_groq_baseline.py
```

This writes `data/eval/groq_predictions.json` with paths relative to this
folder, so the same cache works after uploading `data/eval/` to Colab.

## Class-mix notes

- One vibe per photo: each image is assigned its single dominant
  aesthetic; ambiguous photos were dropped rather than dual-labeled.
- Rooms and outfits live in the same class folder when both apply (the
  upstream pipeline classifies both modes).
- Filenames are not meaningful. Anything ending in `.jpg`, `.jpeg`,
  `.png`, `.heic`, `.heif`, or `.webp` is picked up.
- Class imbalance: the 40-photo cap on the most populous classes was
  chosen to limit head-class dominance during training. The 8-photo
  floor guarantees at least one test image per class for the stratified
  20/20/60 split.

## File format note

iPhone defaults to HEIC. The notebook converts these on the fly via
`pillow-heif`, so no manual conversion is needed. JPEG and PNG work
directly.

## Privacy

Photos in this directory are gitignored (see `data/eval/.gitignore`).
Only the directory structure plus this README is checked in. To share
the dataset for reproducibility, publish it separately and reference the
URL or checksum in the report.
