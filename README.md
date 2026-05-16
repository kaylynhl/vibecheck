# vibecheck

Multi-photo aesthetic (“vibe”) classification + recommendation.

Given one or more photos of a room/outfit, the system will:
1) infer interpretable visual **tags** (palette, lighting, texture/clutter, patterns, silhouette cues)
2) predict the most likely **vibe/aesthetic** (top-k, potentially multi-label)
3) recommend **additions** (items/accessories/decor) and a **playlist** that matches the vibe

## Team
- Julia Kundu (jk2578)
- Sennet Senadheera (sas639)
- Kaylyn Lee (khl62)

---

## Quickstart

### 1) Clone
```bash
git clone https://github.com/kaylynhl/vibecheck.git
cd vibecheck
```

### 2) Install (recommended)
```bash
make setup
```

If you don’t have `make`:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
python -m ipykernel install --user --name vibecheck --display-name "vibecheck"
```

## Image-to-Vibe Pipeline

The backend pipeline turns one or more room/outfit images into structured vibe analysis. It:
- normalizes local image inputs
- calls Groq vision for structured visual analysis
- extracts normalized tags
- scores and ranks likely vibes
- returns a cleaned JSON-ready result for downstream consumers

Main code paths:
- `src/vibecheck/pipeline.py`
- `src/vibecheck/features/`
- `src/vibecheck/tags/`
- `src/vibecheck/vibe/`

Required environment:
- `GROQ_API_KEY` required
- `GROQ_VISION_MODEL` optional override

Current limitations:
- depends on Groq returning valid structured output
- tag extraction and vibe ranking are still heuristic
- the backend stops at analysis; recommendation generation is still downstream work

Easiest next improvements:
- expand tag vocabulary and synonym coverage
- wrap `vibecheck.pipeline.analyze_images(...)` in an API endpoint
- tune score weights with real examples
- replace heuristic matching with learned retrieval/classification later

See `mobile/README.md` for app-facing integration guidance.

---

## Mobile app (iOS)

**Prerequisites:** Node.js 18+, Xcode (for simulator) or [Expo Go](https://apps.apple.com/app/expo-go/id982107779) on your iPhone.

To try the React Native Expo app:

```bash
cd mobile
npm install
npm start
```

If `npm install` fails with peer dependency errors: `npm install --legacy-peer-deps`

**Option A — Expo Go (easiest)**  
1. Install [Expo Go](https://apps.apple.com/app/expo-go/id982107779) on your iPhone  
2. Scan the QR code from the terminal (or enter the URL manually)  
3. Ensure your phone and Mac are on the same WiFi

**Option B — iOS Simulator**  
```bash
npm run ios
```

**Option C — Physical iPhone (dev build)**  
```bash
npx expo run:ios --device
```
Connect your iPhone via USB first. You may need to trust your developer certificate: Settings → General → VPN & Device Management.

> See `mobile/README.md` for full docs, project structure, and backend integration.

---

## Common commands
```bash
make setup   # create venv + install deps + register jupyter kernel
make fmt     # black + isort
make lint    # ruff
make test    # pytest
```

---

## Project structure
```text
vibecheck/
  mobile/           # React Native Expo iOS app
  data/
    raw/            # not committed
    processed/      # not committed
  notebooks/        # exploration only
  src/
    vibecheck/
      features/
      tags/
      vibe/
      rec/
      utils/
  scripts/
  tests/
  outputs/          # not committed
```

> Note: `data/raw`, `data/processed`, and `outputs` are gitignored.

---

## Workflow
- Create a branch per feature: `feature/<name>`
- Open PRs for review before merging to `main`
- Keep notebooks out of core logic; put reusable code under `src/`

---

## Notes
- Python: 3.10+ recommended
- If installs fail on Apple Silicon, try:
  ```bash
  python -m pip install -U pip setuptools wheel
  ```
