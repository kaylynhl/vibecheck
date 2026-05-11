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
| Stronger learned tag->vibe model                         | **not built**                      | --                                                                         |
| Music playlist recommendation                            | **not built**                      | --                                                                         |
| Multi-photo aggregation experiment                       | **not built**                      | --                                                                         |
| Tag F1 / aesthetic accuracy evaluation                   | **not built**                      | --                                                                         |
| FastAPI HTTP server (mobile expects `POST /api/analyze`) | **not built**                      | --                                                                         |
| Mobile app integration (currently 100% mocked)           | **not built**                      | `mobile/`                                                                  |
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

### Step 4 — Train a learned tags->vibe classifier

Goal: replace (or supplement) the hand-weighted scoring in `vibe/catalog.py`
with an actual trained model. The proposal explicitly committed to "baseline
first, then a stronger model we implement ourselves."

Solo-able but slower. Depends on having labeled data.

- Build a small labeled dataset (`data/processed/vibe_train.parquet`):
  - mine `filtered_reddit_texts.csv` for posts that contain one of our
  aesthetic keywords (cottagecore, dark academia, etc.). ConvoKit (Step 1.5)
  makes this easier because we also get post titles.
  - run each post text through `tags/extract.py` to get a tag vector
  - label = the aesthetic word found in the post
  - target ~200-500 examples per aesthetic, but anything is better than zero
- `src/vibecheck/vibe/learned.py`:
  - `train_logreg(X, y) -> sklearn model`  (baseline)
  - `train_mlp(X, y, hidden=64, epochs=20) -> torch model`  (improved)
  - `predict_topk(model, tag_vector, k=3) -> list[(vibe, prob)]`
- `scripts/train_vibe_classifier.py` -- single command, prints metrics
- Compare on a held-out 20% split: hand-weights vs logreg vs MLP, top-1
and top-3 accuracy

Deliverable: a numerical table of baseline vs improved classifier accuracy.
This is the "we trained our own model" claim the rubric is looking for.

### Step 5 — Music playlist recommendation

Goal: produce a playlist whose title matches the inferred vibe.

Solo-able after Step 1.

- Download Kaggle "Spotify Playlists" dataset to
`data/raw/spotify_playlists.csv`
- `scripts/build_playlist_index.py` -- encode each playlist *title* with
`fashion-bert-output-v2` (yes, model is fashion-trained -- if results are
bad, that's a finding to report; we can fine-tune a music-bert later)
- `src/vibecheck/rec/playlists.py` with `recommend_playlist(payload) -> Playlist`
- Wire into `pipeline.analyze_images(with_recommendations=True)`
- Optional: if title-match quality is poor, hand-curate ~50 (vibe,
playlist-title) triplets and fine-tune `music-bert-output-v1` using the
same recipe as fashion-bert

Deliverable: a string vibe query returns a playlist + tracks.

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

### Step 8 — App integration (saved for last on purpose)

Goal: connect mobile to the real backend.

- `src/vibecheck/server/app.py` -- FastAPI app with a single
`POST /api/analyze` route that accepts multipart photos + mode and calls
`analyze_images(with_recommendations=True)`
- `scripts/serve.py` -- `uvicorn vibecheck.server.app:app --reload`
- Add `fastapi`, `uvicorn`, `python-multipart` to `requirements.txt`
- In mobile `app/(tabs)/index.tsx`, switch from `vibeApi.analyzePhotos` to
`vibeApi.analyzePhotosWithBackend`
- Map the backend response shape to the mobile `VibeCheck` type in
`services/api.ts`
- Replace mocked `submitFeedback` with a real `POST /api/feedback` endpoint
that persists to a SQLite file in `outputs/feedback.sqlite` for the
human study

Deliverable: real photo on a real phone -> real recommendations from the real
model.

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
- `requirements.txt`: add `sentence-transformers`, `faiss-cpu`, `fastapi`,
`uvicorn`, `python-multipart`, `convokit` as they get used

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


