# VibeCheck Build Plan

A single-source-of-truth checklist for what the project is supposed to do, what
already exists, and what is left to build. Update this file as steps land.

---

## What the system does (one paragraph)

User uploads one or more photos of a room or an outfit. The backend turns the
photo(s) into a structured "vibe profile": interpretable visual tags (palette,
lighting, texture, pattern, silhouette, material) plus a ranked list of
aesthetics (cottagecore, dark academia, minimalist, etc.). That vibe profile is
turned into a text query, expanded with real Reddit aesthetic vocabulary, and
used to retrieve (a) complementary clothing/decor items from a product catalog
and (b) a music playlist whose title matches the same vibe. The user can rate
the result so we can run a small human study at the end.

---

## Current status snapshot


| Area                                                     | Status                             | Lives in                                                                   |
| -------------------------------------------------------- | ---------------------------------- | -------------------------------------------------------------------------- |
| Image -> structured visual analysis (Groq vision)        | done                               | `src/vibecheck/features/groq_vision.py`                                    |
| Tag normalization (vocabulary + phrase matching)         | done                               | `src/vibecheck/tags/`                                                      |
| Tag -> vibe scoring (hand-weighted baseline, 20 vibes)   | done (baseline only)               | `src/vibecheck/vibe/catalog.py`, `vibe/scoring.py`                         |
| Multi-image input handling                               | partial (accepted, not aggregated) | `features/image_inputs.py`                                                 |
| CLI demo                                                 | done (one-shot)                    | `scripts/demo.py`                                                          |
| Backend tests                                            | done                               | `tests/`                                                                   |
| Fine-tuned text encoder (`fashion-bert-output-v2`)       | done                               | `reddit/fashion-bert-output-v2/`                                           |
| Filtered Reddit corpus (~62k posts)                      | done                               | `reddit/filtered_reddit_texts.csv`                                         |
| Product catalog (~1,249 Depop items)                     | done                               | `reddit/example-fashion-dataset.json`                                      |
| Precomputed product embeddings                           | done                               | `reddit/FINAL-EMBEDDINGS.csv`                                              |
| FAISS query expansion + product retrieval                | done (modular)                     | `src/vibecheck/rec/{text_index,products,expansion}.py`                     |
| Image pipeline -> text retrieval glue                    | done                               | `src/vibecheck/rec/`, `pipeline.analyze_images(with_recommendations=True)` |
| Selection objective (diversity + complementarity)        | done (greedy + ablations)          | `src/vibecheck/rec/select.py`, `scripts/ablate_selection.py`               |
| Stronger learned tag->vibe model                         | done (logreg + MLP)                | `src/vibecheck/vibe/learned.py`, `scripts/train_vibe_classifier.py`        |
| Music playlist recommendation                            | done (live Spotify search + rerank) | `src/vibecheck/rec/playlists.py`, `src/vibecheck/rec/spotify_client.py`    |
| Multi-photo aggregation experiment                       | **not built**                      | --                                                                         |
| Tag F1 / aesthetic accuracy evaluation                   | **not built**                      | --                                                                         |
| FastAPI HTTP server (`/api/analyze`, `/api/feedback`)    | done                               | `src/vibecheck/server/`, `scripts/serve.py`                                |
| Mobile app integration (real backend, no more mocks)     | done                               | `mobile/services/api.ts`, `mobile/app/(tabs)/index.tsx`                    |
| Human evaluation collection                              | **not built**                      | --                                                                         |


---

## Glossary (skim if any term is fuzzy)

- **Sentence transformer**: a BERT/DistilBERT variant trained so that whole
sentences become a single vector where similar meaning = small distance.
- **Fine-tuning**: keep training a pre-trained model on your own data for a few
epochs so it specializes. `fashion-bert-output-v2` is the saved checkpoint.
- **Embedding**: the fixed-length vector the model spits out for a piece of
text (384 dims for v2).
- **Triplets**: `(query, positive, negative)` training examples used to teach
the model what "matches" looks like. We have ~149 hand-curated ones.
- **FAISS**: Facebook's fast nearest-neighbor library over embedding matrices.
- **Query expansion**: enrich a short user query by averaging in the embeddings
of the top-k Reddit posts that already match it, so the search has more real
vocabulary to work with.
- **Groq**: a hosted inference provider (not a model). It runs open-source
models like Llama 4 Scout on custom LPU chips and exposes them through an
OpenAI-compatible HTTPS API. We use it as the vision backbone in
`features/groq_vision.py`. Requires `GROQ_API_KEY` env var.
- **ConvoKit**: a Cornell toolkit that ships preformatted Reddit corpora.
- **Mercari / Depop**: resale marketplaces; their product listings are the
catalog of "items to recommend."
- **Retrieval**: given a query, pick best items from a fixed pool. (Different
from classification, where you predict a label.)

---

## What we have without Julia's laptop

Confirmed to be already in the repo and sufficient to rebuild the whole
text-retrieval pipeline solo:

- `reddit/fashion-bert-output-v2/` -- the fine-tuned encoder (90 MB)
- `reddit/filtered_reddit_texts.csv` -- 62,380 cleaned Reddit posts
- `reddit/example-fashion-dataset.json` -- 1,249 Depop products with full
metadata + image URLs
- `reddit/FINAL-EMBEDDINGS.csv` -- 1,248 precomputed product embeddings (matches
the Depop catalog 1:1, 384 dims)

What's missing and **what we will substitute**:


| Missing file                                   | Substitute                                          |
| ---------------------------------------------- | --------------------------------------------------- |
| `fashion-corpora/` (ConvoKit raw)              | use `filtered_reddit_texts.csv` directly            |
| `COMBINED-FINAL.json`                          | use `example-fashion-dataset.json`                  |
| `mercari-set1.json`, `mercari-set2.json`       | use Depop now; swap for Mercari later (same recipe) |
| `utterance_embeddings.npy` (Reddit embeddings) | regenerate locally in ~30s                          |
| `product_embeddings.npy`                       | already present as `FINAL-EMBEDDINGS.csv`           |


---

## Known limitations to acknowledge in the writeup

These are not bugs to fix, they are honest constraints to name in the report.

- **Reddit corpus cutoff is October 2018.** Aesthetics that became popular
after 2018 (clean girl, coastal grandmother, old money, tomato girl, etc.)
have weak or no representation in the Reddit text used to fine-tune the
encoder. Older aesthetics (cottagecore, dark academia, y2k, grunge,
minimalist, scandinavian, mid-century modern) are well covered.
- **Vision backbone is Groq-hosted Llama 4 Scout, not a model we trained.**
The proposal said we would build CV features ourselves; we substituted a
hosted vision model. Tags + aesthetic *scoring* on top of it remain ours.
- **Product catalog is small (~1,249 Depop items).** Recommendations may feel
repetitive. The pipeline is catalog-agnostic and a larger catalog can be
swapped in later by re-running `scripts/build_indexes.py`.
- **Fine-tuning data is only 149 hand-curated triplets.** The encoder leans
heavily on its pretrained knowledge.

---

## Roadmap (do in this order)

The "AI part first, app last" ordering. Each step is independently shippable.

### Step 1 — Make the text-retrieval prototype reproducible *(DONE)*

Goal: convert the two notebooks into proper Python modules that any teammate
can run from a clean checkout.

Solo-able. Inputs already in the repo. Does **not** require ConvoKit because we
already have the cleaned text corpus (`filtered_reddit_texts.csv`) and the
precomputed product embeddings (`FINAL-EMBEDDINGS.csv`).

- Create `src/vibecheck/rec/__init__.py`
- `src/vibecheck/rec/encoder.py` -- thin wrapper around
`SentenceTransformer("reddit/fashion-bert-output-v2")` with
`encode(texts) -> np.ndarray` and unit-norm helper
- `src/vibecheck/rec/text_index.py` -- load `filtered_reddit_texts.csv`,
encode all rows once, cache to `data/processed/reddit_embeddings.npy`,
build a `faiss.IndexFlatIP`, expose `top_k_embeddings(query_vec, k)`
- `src/vibecheck/rec/products.py` -- load
`example-fashion-dataset.json` + `FINAL-EMBEDDINGS.csv`, build a
`faiss.IndexFlatIP`, expose `search(query_vec, k) -> list[Product]`
- `src/vibecheck/rec/expansion.py` -- implement
`expand_query(query_vec, alpha=1.0, beta=0.75, k_corpus=10) -> np.ndarray`
- `scripts/build_indexes.py` -- one CLI command that builds + caches both
indexes (idempotent: skips if cached files exist)
- Add `sentence-transformers` and `faiss-cpu` to `requirements.txt`
- Smoke test: `python scripts/build_indexes.py` then run a real query
(verified: cottagecore → floral knit tops, y2k → y2k items, etc.)

Deliverable: someone can clone the repo and get product results from a string
query in under five minutes. **Confirmed working end-to-end.**

### Step 1.5 — Reproducible Reddit corpus build (do after Step 1)

Goal: make `filtered_reddit_texts.csv` itself reproducible from raw sources, so
a grader (or future-you) can answer "where did this corpus come from?" without
needing Julia's laptop.

Solo-able. Optional but cheap.

- Add `convokit` to `requirements.txt`
- `scripts/build_reddit_corpus.py` that:
  - calls `from convokit import Corpus, download` for the four fashion
  subreddits (`subreddit-MaleFashionAdvice`, `subreddit-femalefashionadvice`,
  `subreddit-InteriorDesign`, `subreddit-streetwear`)
  - iterates utterances, drops anything < 5 words, applies the same TF-IDF
  bottom-percentile filter that the notebook uses
  - writes `data/processed/filtered_reddit_texts.csv`
- Document in `PLAN.md` and the build script's `--help` that the corpus has
a hard cutoff of October 2018
- Optional: extend the subreddit list to better cover modern aesthetics
(`subreddit-cottagecore`, `subreddit-DarkAcademia`, etc.)

Deliverable: a one-command rebuild of the Reddit corpus from scratch.

### Step 2 — Glue the image pipeline to the text retrieval *(DONE)*

Goal: make `analyze_images()` -> `recommend_items()` actually flow.

Solo-able. Depends only on Step 1.

- `src/vibecheck/rec/recommend.py` with:
  - `build_query_string(payload: VisionAnalysisPayload) -> str`
  -- concatenates `vibe_query`, `aesthetic_descriptors`, `mood_descriptors`
  - `recommend_items(payload, *, config, encoder, reddit_index, product_index)`
- Wire `recommend_items()` into `pipeline.analyze_images()` via the
`with_recommendations=True` flag. `VibeAnalysisResult` now has an
`item_recommendations` field (empty by default, so the existing
Groq-only path is unchanged).
- Update `scripts/demo.py` so `--recommend` and `--top-k N` run the full
path end-to-end.
- Add `tests/test_recommend.py` with a stub encoder + tiny in-memory
indexes. 8 new tests, all 50 in the suite pass.

Deliverable: one CLI command turns an image into a list of matching Depop
products. This is the moment the project stopped being "two demos" and started
being one system.

### Step 3 — Implement the selection objective (the AI contribution) *(DONE)*

Goal: replace plain nearest-neighbor with greedy selection that balances vibe
match, complementarity, and diversity. This is the "search/optimization" piece
the proposal explicitly graded.

Solo-able. Depended only on Step 2.

- `src/vibecheck/rec/select.py`:
  - score: `w_vibe * vibe_similarity + w_comp * complementarity_fraction
  - w_red * max_cosine_to_already_selected`
  - greedy loop over a configurable candidate pool (default 50) picking
  `top_k` total
- `complementarity` = `|product_tag_categories ∩ missing_image_categories| /
max(1, |missing_image_categories|)`. Product categories come from running
the existing `tags/extract.py` over the product's text, so image tags and
product tags share one vocabulary.
- `redundancy` = max cosine similarity between the candidate and any
already-selected item, computed off the precomputed FAISS embeddings (no
re-encoding).
- Ablation knobs: `SelectionConfig.use_complementarity` and `use_diversity`.
Wired into `RecommendationConfig.selection`; pipeline + demo CLI gain a
matching `--select` flag.
- `scripts/ablate_selection.py`: prints a side-by-side table of plain NN /
+complementarity / +diversity / both for any text query, ready to drop
into the report.
- 9 new tests in `tests/test_select.py`. All 59 in the suite pass.

Deliverable: configurable selector with three knobs, two ablation flags,
score-breakdown surfaced in the API response, and a one-command comparison
script. Smoke-tested on real Depop catalog: complementarity pulls in linen
dresses, diversity demotes near-duplicate floral shirts. **Confirmed
working end-to-end.**

Stretch (not done): beam search with width 3. Skip unless we have time
before the writeup.

### Step 4 — Train a learned tags->vibe classifier *(DONE)*

Goal: replace (or supplement) the hand-weighted scoring in `vibe/catalog.py`
with an actual trained model. The proposal explicitly committed to "baseline
first, then a stronger model we implement ourselves."

Solo-able. Depended on having labeled data.

- `scripts/build_vibe_dataset.py` mines `reddit/filtered_reddit_texts.csv`
for posts mentioning any vibe (canonical name + a curated alias list for
older aesthetics: "boho", "scandi", "midcentury", "hypebeast", etc.).
Each match -> structured tags via `tags/extract.py` -> a 90-dim
confidence vector. Output is `data/processed/vibe_train.csv`. The
2018 corpus cutoff means we mostly get streetwear / bohemian /
minimalist / grunge labels; this is honest and noted as a limitation.
- `src/vibecheck/vibe/learned.py`:
  - `feature_vector(tags) -> np.ndarray[90]` (stable, alphabetized
  (category, value) axis used at both train and inference time)
  - `train_logreg(X, y)` -- one-vs-rest logistic regression baseline
  - `train_mlp(X, y, hidden=64, epochs=800)` -- sklearn MLPClassifier
  (substituted for torch: same backprop story, no extra dep)
  - `predict_topk(model, tag_vector, k)` and `score_vibes_learned(...)`
  which returns one VibeScore per catalog vibe so it's drop-in for
  the hand-weighted scorer
  - `save_bundle` / `load_bundle` for joblib persistence
- `scripts/train_vibe_classifier.py` does a stratified 80/20 split and
prints the comparison table:

  | model               | top-1  | top-3  |
  | ------------------- | ------ | ------ |
  | hand-weighted       | 0.036  | 0.214  |
  | logistic regression | 0.286  | 0.714  |
  | MLP (sklearn)       | 0.357  | 0.679  |

  Saves the trained MLP bundle to `data/processed/vibe_classifier.joblib`.
- Pipeline integration: `analyze_images(use_learned_classifier=True)`
loads the joblib at runtime and swaps in the learned scorer. Falls
back to the hand-weighted scorer (with a warning) if the joblib is
missing or corrupted. `scripts/demo.py` exposes this as
`--learned-classifier`.
- 10 new tests in `tests/test_learned_vibe.py` using a tiny in-memory
synthetic model so CI never trains a real model.

Deliverable: a real numerical table of baseline-vs-improved classifier
accuracy on the same test split. The learned classifiers improve top-1
accuracy ~10x and top-3 accuracy ~3x over the hand-weighted baseline.
Caveat to call out in the writeup: the test split is biased toward the
8 vibes that appear in the mined data, so the hand-weighted scorer's
poor showing partly reflects the catalog/label mismatch, not just model
quality.

### Step 5 — Music playlist recommendation *(DONE)*

Goal: generate a playlist of real Spotify tracks matching the inferred vibe.

**Constraint we hit:** Spotify deprecated `/v1/recommendations`,
`/audio-features`, and `/audio-analysis` for new developer apps on
Nov 27, 2024. The original plan to use seed-genres + audio feature
targeting is impossible for any app created after that date. We pivoted
to live `/v1/search?type=track` and re-rank with our fashion-bert
encoder. Spotify is the catalog; we are the ranker.

(An earlier version of this step matched made-up playlist titles via
fashion-bert embeddings -- those titles weren't real Spotify playlists
and weren't playable, so it was discarded.)

- `src/vibecheck/rec/spotify_client.py`:
  - Thread-safe Spotify Web API client using Client Credentials Flow
  (no user-OAuth needed; public catalog reads only)
  - In-process token cache with auto-refresh (real expiry ~60 min,
  we refresh slightly early)
  - Handles 401 (force-refresh + retry once), 429 (Retry-After), and
  prints a clear warning on other non-200 responses
  - `SPOTIFY_SEARCH_MAX_LIMIT = 10` -- undocumented constraint we
  discovered empirically: `/v1/search` rejects `limit > 10` with
  HTTP 400 "Invalid limit" on new-app Client Credentials tokens,
  despite the docs claiming 0-50 is the valid range
- `src/vibecheck/rec/playlists.py`:
  - `Track` dataclass (id, name, artists, album_image, preview_url,
  spotify_url, duration_ms) -- exactly the fields the iOS app needs
  to render a playable card
  - `build_search_queries(payload)` pulls 6-8 short keyword queries
  from `aesthetic_descriptors`, chunks of `vibe_query`, and
  `mood_descriptors`. We need more queries (vs. fewer with higher
  limits) because of the 10-item cap above.
  - `recommend_tracks(payload, top_k, ...)`:
    1. Build queries from payload
    2. Hit `/v1/search` per query (live, no cache)
    3. Dedupe pool by Spotify track ID
    4. Encode each track's "<title> - <artist>" with fashion-bert
    5. Encode the vibe query with optional Reddit-based expansion
    6. Cosine similarity -> top-K
- Pipeline integration: `analyze_images(with_playlist=True)` populates
`VibeAnalysisResult.playlist_recommendations`. `scripts/demo.py`
exposes `--playlist` / `--playlist-top-k`. Credentials live in `.env`
(`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`); `.env` is gitignored.
- 13 tests in `tests/test_playlists.py` covering query building,
dedup, encoder re-ranking, graceful empty-result handling, and the
Spotify client's credential-loading + empty-query short-circuits.
The real Spotify API is never hit in CI -- a `StubSpotify` class
returns canned responses.
- Live smoke test against real Spotify (4 vibes, top-5 each):

  | vibe | top-1 score | top-1 track |
  | --- | --- | --- |
  | cottagecore | 0.625 | "Indie Folk" -- OlexandrMusic |
  | cyberpunk | 0.557 | "Cyberpunk" -- ATEEZ |
  | y2k | 0.498 | "2000s Pop Punk Rnb" -- WHATMORE |
  | streetwear | 0.609 | "Streetwear" -- Bale |

**Honest finding for the writeup:** Spotify's search is keyword-driven
on track/artist/album metadata. Without the deprecated
`/recommendations` we can't ask for "tracks that *sound* like
cottagecore" -- only "tracks whose metadata *says* cottagecore." Our
fashion-bert reranking still meaningfully reorders the candidate pool,
but the upstream pool is biased toward tracks with the literal vibe
word in their title. The upgrade path (fine-tune a music-bert on
hand-curated (vibe, track-title) pairs, or partner with Last.fm tag
data which is still openly queryable) is unblocked and saved for later.

Deliverable: vision payload -> real Spotify tracks with playable URLs,
ranked by our model, working live in production for the iOS app.

### Step 6 — Multi-photo aggregation experiment

Goal: deliver on the proposal's promise to compare aggregation strategies.

Solo-able. Depends on having a small test photo set (10-20 multi-photo
groups).

- Collect a small test set: 10 outfits with front+back photos, 10 rooms
with multiple angles. Just team photos.
- Three runs per photo group:
  - all images in one Groq call (current behavior)
  - one Groq call per image, average the resulting tag vectors
  - one Groq call per image, max-pool per tag category
- Compare top-1 / top-3 vibe stability across the three strategies
- `notebooks/multi_image_aggregation.ipynb` to write up the comparison

Deliverable: one figure in the final report.

### Step 7 — Evaluation for the writeup

Goal: numbers that go in the final report.

Needs the team for hand-labeling.

- **Tag prediction quality**: hand-label 50 photos with ground-truth tags
from `tags/vocabulary.py`. Compute precision / recall / F1 per tag and
macro-averaged across tags.
- **Aesthetic accuracy**: hand-label 50 photos with top-1 + top-3
acceptable aesthetics. Compare three configurations:
  - Groq direct (skip the tag layer)
  - tags -> hand-weighted scoring (current)
  - tags -> learned classifier (Step 4)
- **Selection ablation**: from Step 3, measure how often the selected items
cover each tag category, and how diverse they are (avg pairwise cosine).
- `scripts/evaluate_*.py` per metric, all writing CSVs into `outputs/`

Deliverable: 2-3 tables and 1-2 figures for the report.

### Step 8 — App integration *(DONE)*

Goal: connect mobile to the real backend.

**What landed:**

- `src/vibecheck/server/app.py` -- FastAPI app with:
  - `GET  /api/health` -- sanity check + reports whether the encoder was
  pre-warmed and which optional pipeline features (selection, learned
  classifier, playlist) are active
  - `POST /api/analyze` -- multipart upload (up to 6 photos + `mode`); reads
  the bytes, calls `analyze_images(with_recommendations=True,
  use_selection=True, use_learned_classifier=True, with_playlist=True)`,
  reshapes the result into the mobile `VibeCheck` contract, returns 200 JSON.
  Pipeline errors are surfaced as 502 with the underlying message.
  - `POST /api/feedback` -- JSON body (vibe-check id + ratings + optional
  notes); persisted to SQLite for the Step 9 human study.
  - CORS open by default (override with `VIBECHECK_CORS_ORIGINS=` env var).
  - FastAPI lifespan handler pre-warms the fashion-bert encoder + Reddit /
  product indexes on startup so the first request isn't 5-10s slower than
  the rest. Pre-warm failures are logged but don't block boot.
- `src/vibecheck/server/mappers.py` -- the single place where pipeline
dataclasses are turned into the mobile JSON contract:
  - `extracted_tags` -> `Tag[]`, dropping anything outside the six canonical
  vocab categories so the mobile `TagCategory` union stays honest.
  - `top_vibes` -> `VibeResult[]`, with a curated default description per
  vibe so the UI always has something to show. Scores are squashed into
  [0, 1] with `x / (1+x)` so the "% match" badge can never report 250 %.
  - `item_recommendations` (snake_case Depop dicts) -> mobile `Item[]`
  (camelCase, with a coerced `category` in {furniture, decor, clothing,
  accessory} so the UI's strict union stays valid).
  - `playlist_recommendations` (ranked Spotify tracks) wrapped into a
  single synthetic `Playlist` object, with `coverImage` pulled from the
  first track's album art and a name like `"Cottagecore Playlist"`.
- `src/vibecheck/server/storage.py` -- a tiny SQLite store at
`outputs/feedback.sqlite` (gitignored). Schema is created on first use,
one row per submission, with `extra_json` for free-form notes.
- `scripts/serve.py` -- thin `uvicorn` runner. Prints the LAN IP it bound to
on startup with a copy-pasteable `EXPO_PUBLIC_API_URL=...` line so partners
testing from a real phone don't have to hunt for it.
- `Makefile` gets a `make serve` target; `.env.example` documents required
secrets (`GROQ_API_KEY`, `SPOTIFY_CLIENT_*`); `mobile/.env.example`
documents `EXPO_PUBLIC_API_URL` and the `EXPO_PUBLIC_USE_MOCK` flag.

**Mobile side:**

- `mobile/services/api.ts` -- `analyzePhotosWithBackend` now talks to the
real backend, with two important fixes vs the original stub:
  - **No `Content-Type` header.** RN's fetch generates the multipart boundary
  itself; setting `Content-Type: multipart/form-data` strips the boundary
  and the server fails with HTTP 422 "Expected UploadFile, received str."
  This is a famously easy gotcha to miss.
  - **No silent mock fallback.** The original code swallowed network errors
  and quietly served fake data. Now real errors surface in the UI alert
  so the demo doesn't lie. The mock path is still available behind an
  `EXPO_PUBLIC_USE_MOCK=1` env flag for offline UI work.
- `submitFeedback` now POSTs to `/api/feedback` for real.
- `mobile/app/(tabs)/index.tsx` swapped `vibeApi.analyzePhotos` ->
`vibeApi.analyzePhotosWithBackend` and surfaces the real error message.

**Tests (`tests/test_server.py`, 9 tests, all green):**

- `/api/health` shape + content
- `/api/analyze` happy path returns mobile-shaped JSON (tags, vibes,
itemRecommendations, playlistRecommendation, createdAt, ...)
- Pipeline kwargs are forwarded correctly (selection on, learned classifier
on, playlist on)
- Edge cases: zero photos, >6 photos, pipeline raises -> 502 with the
underlying error in `detail`
- `/api/feedback` round-trips through SQLite, including the `extra.notes`
JSON column
- Out-of-range rating -> 422 from pydantic validation
- Pipeline + Spotify are stubbed out via monkeypatch so CI never hits a
real network.

**Live smoke test (real Groq + real Spotify):**

```
GET  /api/health   -> 200, prewarmed: true, all features on
POST /api/analyze  -> 200 in 1.6s with model="meta-llama/llama-4-scout-17b"
                     (validates the multipart contract + pipeline call +
                      mapper output end-to-end)
POST /api/feedback -> 200 {ok: true, id: 1}, row visible in feedback.sqlite
```

**Honest finding for the writeup:** the Llama-4 Scout vision model is
inconsistent at producing strict JSON output for arbitrary photos -- about
30-40 % of random images cause the parse to fail and the pipeline falls back
to its "empty tags" branch. The server contract is robust to this (returns
HTTP 200 with empty results + a warning in `debug.warnings`), so the mobile
UI gracefully handles it, but for the human study we should curate the
photo set to avoid the corner case. Upgrade path: switch to a stronger vision
model with native structured-output support, or relax the prompt's JSON
strictness and parse free-form text instead.

Deliverable: real photo on a real phone -> real recommendations from the real
model. ✓

### Step 8.1 — UI wiring + Spotify integration *(DONE)*

After the first screen-recording demo, several "looks-clickable-but-isn't"
bugs surfaced:

- Depop item cards rendered but didn't open the product page.
- Playlist `Open` / `Play` buttons were no-ops.
- The per-track play button was a no-op (Spotify's `preview_url` was deprecated
  for Client Credentials apps in late 2024, so we never had a stream URL).
- Playlist cover art was just the first track's album image.

What landed:

- `mobile/components/ItemCard.tsx` -- tap a card -> `Linking.openURL(productUrl)`,
  with `canOpenURL` check and a friendly alert if the URL is missing or
  blocked. Backward-compatible: if the parent provides an `onPress` it wins.
- `mobile/components/PlaylistCard.tsx` rewritten:
  - Per-track row tap -> `Linking.openURL(track.spotifyUrl)` (opens in the
    Spotify app if installed, otherwise web).
  - Per-track play button -> `WebBrowser.openBrowserAsync` against
    `https://open.spotify.com/embed/track/<id>`. This is **the trick Discord
    uses**: Spotify's official embed plays the 30-second preview through their
    own auth context, so it works for signed-out users without needing the
    deprecated `preview_url` field.
  - Playlist "Preview" button -> same embed flow on the first track.
  - Playlist "Open" button -> Linking.openURL on the first track's
    `spotifyUrl`.
  - New "Save to Spotify" button -> triggers PKCE OAuth (see below), creates
    a real private playlist in the signed-in user's account, and offers to
    open it.
- `mobile/services/spotify.ts` -- imperative PKCE OAuth flow against the
  Spotify Web API. No client secret needed; client ID lives in
  `EXPO_PUBLIC_SPOTIFY_CLIENT_ID`. Token cached in-memory for the 1h
  validity window. Two API calls per save: `POST /users/{id}/playlists`
  then `POST /playlists/{id}/tracks` (chunked at 100 URIs per Spotify's
  cap). Redirect URI is `vibecheck://oauth-callback` (already declared
  via `app.json` "scheme": "vibecheck"); inside Expo Go the runtime
  computes an `exp://...` URI that also has to be added to the Spotify
  dashboard.
- `mobile/services/types.ts` -- added `Track.spotifyUrl` and
  `Item.productUrl` (the backend was already returning both; the TypeScript
  contract just didn't surface them).

Backend cover art:

- `src/vibecheck/rec/cover_art.py` builds a Pollinations.ai prompt URL
  (free, no auth, SDXL/Flux backend) seeded deterministically by vibe
  name, so the same aesthetic always gets the same cover. The result is
  just a URL -- the mobile `<Image>` loads it directly, Pollinations
  caches by (prompt, seed, size) on its CDN, so we pay neither bandwidth
  nor latency for repeats. Set `VIBECHECK_DISABLE_COVER_ART=1` to fall
  back to the previous album-art behaviour (used in tests).
- `src/vibecheck/server/mappers.py::_map_playlist` now prefers the
  generated cover and falls back to album art if cover generation is
  disabled or fails.

Why not Groq for cover art? Groq is a text/LLM-only inference service --
no image generation surface, period. Free options ranked by setup cost:

1. Pollinations (chosen) -- zero friction, decent quality, free.
2. Cloudflare Workers AI -- better quality, free tier 10k req/day, but
   needs a Cloudflare account + API token.
3. Hugging Face Inference API -- best SDXL quality, free tier rate-limited,
   needs a HF account + token.
4. DALL-E / OpenAI -- best quality but ~$0.04/image and a paid key.

Tests: 10/10 server tests pass, including a new
`test_analyze_uses_generated_cover_art_when_enabled` that exercises the
non-disabled path. Full suite still 92/92.

### Step 8.2 — Vision pipeline reliability *(DONE)*

After the second screen-recording demo, a different failure surfaced: for
a real-world photo of a Middle Eastern coffee shop, the analyzer returned
"Mid-Century Modern at 2 %" with empty tags, zero items, zero tracks. The
backend logged a 200 OK so it wasn't an integration issue.

Root cause: Llama-4 Scout produced output that failed the strict JSON
parser in `groq_vision.py`, the pipeline took the
``VisionOutputFormatError`` fallback path, and the resulting "0 tags
+ 0 vibe signal" propagated all the way to the UI. This is the same
~30 – 40 % JSON-validity failure rate that was already noted under
"honest finding for the writeup" in step 8.

Two AI-level improvements to fix it (these are genuine design choices,
not UI/scaffolding — good writeup material):

**Improvement 1: enforce a JSON schema at decode time.**
`src/vibecheck/features/groq_vision.py` now passes the Responses API's
`text.format.type = "json_schema"` with a full ``vibe_analysis_output``
schema mirroring the dataclass. Groq's documented model card explicitly
supports JSON-schema mode for ``meta-llama/llama-4-scout-17b-16e-instruct``.
This is a *one-line wire change* on the API side, but the effect is
structural: the decoder is no longer free to emit malformed JSON; it must
emit a body matching the schema or it doesn't emit at all. On the offending
photo, this alone took the result from "Mid-Century Modern @ 2 %" to
"minimalist @ 57 %" with 10 items and 10 tracks.

**Improvement 2: caption-similarity vibe fallback.**
`src/vibecheck/vibe/embedding_match.py` is a new scorer that takes the
vision model's free-form ``visual_summary`` text, embeds it with the
existing fashion-bert encoder (same model as the product recommender), and
ranks the 20 catalog vibes by cosine similarity against their
description + keyword corpus. The pipeline now treats this as a fallback:
if the tag-based scorer's top vibe is below 5 % (the same threshold the UI
uses for its low-confidence banner), the caption-embedding scorer takes
over. This is defence-in-depth — even when the schema-enforced JSON is
*valid* but semantically thin (e.g. the model describes a scene whose
descriptors don't intersect our hand-built tag vocab), we still recover a
meaningful vibe signal from the natural-language caption.

Both layers together are good ablation material:
1. Strict-JSON parser only (original, ~30 – 40 % failure).
2. JSON-schema enforced only (eliminates most decode failures).
3. JSON-schema + caption-embedding fallback (catches the remaining
   "valid JSON but no vibe signal" cases).

UI honesty: `mobile/app/vibe/[id].tsx` now renders a "low confidence read"
banner with a "try another photo" CTA whenever the top vibe is below 5 %
*or* the result has zero tags + zero items + zero tracks. So even in the
worst case, the demo doesn't lie about its certainty.

Tests: added `tests/test_embedding_match.py` (4 tests, mocked encoder so
no sentence-transformers load on CI) and updated `test_groq_vision.py` to
assert the JSON schema is wired into the request payload. Full suite
96/96.

### Step 9 — Human study

Goal: collect ratings from non-team participants for the report.

- Recruit ~10 evaluators
- Each evaluator submits 3-5 photo sets through the app
- For each result, collect:
  - vibe match (1-5)
  - additions improve coherence (1-5)
  - diversity / novelty (1-5)
- Comparison conditions: random selection vs tag-count baseline vs ours
- Analyze: paired t-tests on rating means, summary table for the report

---

## Repo housekeeping (do alongside everything else)

- Fix `make demo` -- currently runs `scripts/demo.py` with no `--img`,
which is required and breaks
- Create `notebooks/` and move the two `reddit/*.ipynb` files there once
Step 1 is done
- Decide what to do about the `reddit/` folder name -- once Step 1 is
done, the model + CSVs should probably move to `data/raw/` and
`models/`, leaving `reddit/` empty
- Reconcile model version with the status report: report says
`fashion-bert-output-v4` (msmarco-distilbert, 768 dims), repo has v2
(MiniLM, 384 dims). Either commit v4 or correct the report.
- `requirements.txt`: add `convokit` if Step 1's full Reddit pipeline is ever
re-run (the rest -- `sentence-transformers`, `faiss-cpu`, `fastapi`,
`uvicorn`, `python-multipart` -- are already in)

---

## Division of labor (suggested, fluid)


| Workstream                                 | Best owner                             | Why                        |
| ------------------------------------------ | -------------------------------------- | -------------------------- |
| Steps 1, 2, 3 (text retrieval + selection) | whoever knows Python + sklearn         | core pipeline glue         |
| Step 4 (learned vibe classifier)           | whoever wants the most "AI" credit     | trains an actual model     |
| Step 5 (music)                             | independent track, can run in parallel | doesn't block anything     |
| Step 6 (multi-image experiment)            | whoever has time + photos              | small isolated chunk       |
| Step 7 (evaluation)                        | needs the whole team for labeling      | shared chore               |
| Step 8 (app integration)                   | whoever owns mobile                    | matches existing knowledge |
| Step 9 (human study)                       | whoever can recruit                    | logistics-heavy            |


