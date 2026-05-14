# Labeled aesthetic dataset

This directory is the **labeled dataset** used to evaluate and train the
CLIP-LoRA aesthetic classifier (see `notebooks/demo.ipynb`).

It is also used as a fixed held-out test set to compare:

1. Groq Vision (Llama-4 Scout, current production baseline)
2. CLIP-ViT-B/32 zero-shot (prompted, no training)
3. CLIP-ViT-B/32 linear probe (trained head, frozen backbone)
4. CLIP-ViT-B/32 + LoRA (fine-tuned rank-8 adapters on the vision tower) **← ours**

## Readiness check

Before spending Groq credits or opening the Colab notebook, run:

```bash
python scripts/check_eval_dataset.py
```

The default gate is **8 photos per class**. For the healthier target from the
handoff, use:

```bash
python scripts/check_eval_dataset.py --min-per-class 12
```

Once the check passes, cache the production Groq baseline:

```bash
python scripts/export_groq_baseline.py
```

This writes `data/eval/groq_predictions.json` with paths relative to this
folder, so the same cache works after uploading `data/eval/` to Colab.

## Folder = label

Every photo's label is its parent directory name. The 8 supported classes:


| Folder                 | Aesthetic           | What to photograph                                                                                                             |
| ---------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `minimalist/`          | minimalist          | Clean lines, restrained palette, lots of empty space. Modern apartments, white kitchens, single-color outfits, IKEA-but-fancy. |
| `dark_academia/`       | dark academia       | Old books, leather, plaid, brass, warm low light. Libraries, study desks, tweed jackets, vintage wood.                         |
| `cottagecore/`         | cottagecore         | Florals, linen, soft wood, gingham, garden plants, brunch spreads, vintage china. Sunlit kitchens, picnic outfits.             |
| `grunge/`              | grunge              | Distressed denim, band tees, graffiti, basements, mosh-pit energy. Anything that would look at home on early-2000s Tumblr.     |
| `coastal_grandmother/` | coastal grandmother | Wicker, breezy linen, blue-and-white striped textiles, beach houses, Diane Keaton hats.                                        |
| `scandinavian/`        | scandinavian        | Pale wood, white walls, neutral textiles, hygge candles, sheepskin throws. (Different from "minimalist" — it's *warmer*.)      |
| `mid_century_modern/`  | mid-century modern  | Walnut furniture, low-slung sofas, Eames chairs, geometric patterns, mustard / olive / teal accents.                           |
| `japandi/`             | japandi             | Japanese minimalism × Scandinavian warmth: tatami, low tables, raw wood, indigo textiles, MUJI-meets-Kinfolk.                  |


## Collection rules

- **Personal photos only.** You (or friends, with permission) take them. No
Pinterest / Unsplash scraping for this dataset. The "I built this myself"
claim in the report depends on this.
- **One vibe per photo.** Pick the *dominant* aesthetic. If a photo
legitimately has two strong vibes (e.g. a japandi-leaning minimalist
bedroom), pick whichever is stronger and skip the borderline ones.
- **At least 8 photos per class.** 12 is better. With 8 classes × 8 photos
= 64 photos, our train/val split is workable but tight; 12 × 8 = 96 is
much healthier.
- **Filename doesn't matter.** Anything ending in `.jpg / .jpeg / .png / .heic` is picked up. Phone defaults like `IMG_4231.jpg` are fine.
- **Try to vary the framing.** Different angles, different rooms, different
lighting. If all your minimalist photos are the same shelf from 3 angles,
the model overfits to that shelf.
- **Mode mix is OK.** Rooms and outfits can both go in the same class
(the existing pipeline labels both modes anyway).

## File format note

iPhone defaults to HEIC. The notebook converts these on the fly via
`pillow-heif`, so you don't need to convert manually. If you're on Android  
or saving from web, JPEG/PNG works directly.

## Privacy

Photos in this directory are **gitignored** (see `data/eval/.gitignore`).
We never commit personal photos. Only the directory structure + this
README is checked in. If you want to share a dataset for reproducibility,
publish it separately and reference a URL/checksum in the report.
