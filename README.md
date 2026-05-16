# vibecheck

Multi-photo aesthetic ("vibe") classification + recommendation.

Given one or more photos of a room or outfit, the system will:
1. Infer interpretable visual **tags** (palette, lighting, texture/clutter, patterns, silhouette cues).
2. Predict the most likely **vibe / aesthetic** using a CLIP-LoRA classifier trained on 20 aesthetic classes.
3. Recommend matching **items** (clothing / decor) and a **Spotify playlist**.

The repo has two runnable pieces:
- A Python FastAPI backend that runs the ML pipeline (`src/vibecheck/`, served by `scripts/serve.py`).
- An Expo React Native iOS app that talks to the backend over HTTP (`mobile/`).

## Team
- Julia Kundu (jk2578)
- Sennet Senadheera (sas639)
- Kaylyn Lee (khl62)

---

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Either Xcode (iOS simulator) or [Expo Go](https://apps.apple.com/app/expo-go/id982107779) on a physical iPhone
- A free Groq account → [console.groq.com](https://console.groq.com)
- A free Spotify developer app → [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)

---

## 1. Run the backend (FastAPI)

### 1.1 Clone and install

```bash
git clone https://github.com/kaylynhl/vibecheck.git
cd vibecheck
make setup
```

This creates `.venv/`, installs everything in `requirements.txt`, and registers a Jupyter kernel called `vibecheck`.

If you don't have `make`:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

### 1.2 Configure backend API keys

Copy the example env file and fill it in:
```bash
cp .env.example .env
```

Open `.env` and set these values (the file is loaded by `src/vibecheck/server/app.py` via `python-dotenv`, so any process started from the repo root picks them up):

| Variable | Where to get it | Required for |
|---|---|---|
| `GROQ_API_KEY` | console.groq.com → API Keys → Create | Image → tags (every `/api/analyze` request) |
| `SPOTIFY_CLIENT_ID` | developer.spotify.com/dashboard → Create app → copy "Client ID" | Album cover art + the mobile PKCE flow |
| `SPOTIFY_CLIENT_SECRET` | Same Spotify dashboard, same app → "View client secret" | Backend Spotify token exchange |

The remaining vars in `.env.example` (`VIBECHECK_CORS_ORIGINS`, `VIBECHECK_HOST`, `VIBECHECK_PORT`, `VIBECHECK_RELOAD`) are optional; defaults are fine for local dev.

> Both `.env` files are gitignored. Only the `.env.example` templates are committed.

### 1.3 Start the server

```bash
make serve
```

This runs `python scripts/serve.py`, which launches uvicorn on `0.0.0.0:8000` with autoreload and prints:
- `http://localhost:8000` — for the iOS simulator
- `http://<your-laptop-LAN-ip>:8000` — for a real iPhone on the same Wi-Fi
- The exact `EXPO_PUBLIC_API_URL=...` line to drop into `mobile/.env`

Sanity-check it from another terminal:
```bash
curl http://localhost:8000/api/health
```

A healthy response looks like `{"ok": true, "prewarmed": true, ...}`. The first hit takes ~10s because the server pre-warms the FashionBERT encoder and FAISS indexes on startup.

---

## 2. Run the mobile app (Expo)

```bash
cd mobile
npm install        # if peer-dep errors: npm install --legacy-peer-deps
```

### 2.1 Configure mobile env

```bash
cp .env.example .env
```

Open `mobile/.env` and set:

| Variable | What to put | Notes |
|---|---|---|
| `EXPO_PUBLIC_API_URL` | `http://localhost:8000` (simulator) **or** `http://<laptop-LAN-ip>:8000` (real iPhone) | The LAN URL is printed by `make serve` |
| `EXPO_PUBLIC_SPOTIFY_CLIENT_ID` | The **public** Client ID from the same Spotify dashboard app you used for the backend | PKCE — no secret on device |
| `EXPO_PUBLIC_USE_MOCK` | leave blank | Set to `1` to force the offline mock pipeline (UI work only) |

In the Spotify developer dashboard, also add these to the app's **Redirect URIs**:
- `vibecheck://oauth-callback` (standalone build)
- The `exp://...` URL that Metro prints when you run `npm start` (for Expo Go)

### 2.2 Launch

```bash
npm start
```

Then pick one:
- **Expo Go (easiest):** scan the QR code from your iPhone. Phone + laptop must be on the same Wi-Fi, and `EXPO_PUBLIC_API_URL` must point to the laptop's LAN IP.
- **iOS simulator:** `npm run ios`
- **Physical iPhone via USB (dev build):** `npx expo run:ios --device`

---

## 3. Reproduce the CLIP-LoRA evaluation (`notebooks/demo.ipynb`)

This notebook produced the rank-ablation, per-class heatmap, and confusion-matrix figures used in the final report.

We trained a LoRA-fine-tuned CLIP-ViT-B/32 image classifier on a labeled photo set covering the 20 aesthetic categories under `data/eval/`. The notebook walks through data loading, two baselines, our LoRA fine-tune, a rank ablation, and the final comparison.

Systems compared on the same held-out test split:
1. **CLIP zero-shot** — frozen CLIP with class-name prompts.
2. **CLIP linear probe** — frozen CLIP features, sklearn logistic regression head.
3. **CLIP + LoRA (ours)** — rank-{1, 4, 8, 16} adapters on the vision tower; **r = 8** is what production ships.

The full pipeline runs in roughly 15–25 minutes on a Colab T4 GPU.

### 3.1 Run on Colab

1. Open `notebooks/demo.ipynb` in Colab: **File → Open notebook → GitHub tab → `kaylynhl/vibecheck` → `notebooks/demo.ipynb`**.
2. Set the runtime to **T4 GPU** (Runtime → Change runtime type).
3. Click **Run all**.
4. When the first cell prompts you, upload `data_eval.zip` (see 3.2).

The last cell exports all report figures to `plots_for_report/*.png` and zips them for download.

### 3.2 Where to get `data_eval.zip`

- **In this repo:** `data_eval.zip` is committed to the repo root (~17 MB).
- **Via Google Drive:** the link is in the Project Report document if you don't have a local checkout.

The zip is a flat archive of `data/eval/<aesthetic>/*.jpg` covering all 20 classes (~518 photos total).

---

## 4. Common commands

```bash
make setup          # create venv + install deps + register jupyter kernel
make serve          # run FastAPI backend (uvicorn, :8000, autoreload)
make test           # pytest
make fmt            # black + isort
make lint           # ruff
make eval-check     # print per-class photo counts under data/eval/
make groq-baseline  # cache Groq Vision predictions for the eval set
make clean          # remove caches + build artifacts
```

---

## Project structure

```text
vibecheck/
  mobile/                          # React Native Expo iOS app
  src/vibecheck/
    pipeline.py                    # end-to-end image -> vibe + recs entry point
    features/groq_vision.py        # Groq vision feature extraction
    vibe/clip_lora.py              # CLIP + LoRA aesthetic classifier (production)
    rec/                           # retrieval + selection for items + playlists
    server/app.py                  # FastAPI app
  notebooks/demo.ipynb             # CLIP-LoRA training + ablation + plots
  data/eval/<aesthetic>/           # labeled images (gitignored; ships in data_eval.zip)
  data_eval.zip                    # bundled image set for Colab
  models/clip_lora/                # production LoRA adapters + classifier head
  plots_for_report/                # exported figures (gitignored)
  scripts/                         # helper scripts (serve, eval-check, ...)
  tests/                           # pytest suite
```

---

## Notes

- Python 3.10+ recommended.
- If installs fail on Apple Silicon, run `python -m pip install -U pip setuptools wheel` before `pip install -r requirements.txt`.
- The backend pre-warms the encoder + FAISS indexes on startup, so the first `/api/analyze` call takes ~10s; subsequent calls are fast.
- `data/eval/<class>/*.{jpg,png,heic,…}` is gitignored — the canonical training/eval set ships as `data_eval.zip`.
