"""FastAPI HTTP backend for the VibeCheck mobile app.

Endpoints:
    GET  /api/health      sanity check + pre-warm status
    POST /api/analyze     multipart: photos[] + mode -> mobile-shaped VibeCheck
    POST /api/feedback    JSON: vibeCheckId + ratings -> {ok: true}

Run with:
    uvicorn vibecheck.server.app:app --host 0.0.0.0 --port 8000 --reload
or:
    python scripts/serve.py

The app pre-warms the encoder, FAISS indexes, and Spotify token once on
startup so the first ``/api/analyze`` request isn't 15s slower than the rest.
Failures during pre-warm are logged but don't block startup -- requests will
get the same error surface they would have anyway.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from vibecheck.pipeline import analyze_images
from vibecheck.server.mappers import map_result_to_vibe_check
from vibecheck.server.storage import record_feedback

load_dotenv()

logger = logging.getLogger("vibecheck.server")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


# ---------- request / response schemas ----------

VibeMode = Literal["room", "outfit"]


class FeedbackRequest(BaseModel):
    """Payload mirrors the mobile `submitFeedback` call site."""

    vibeCheckId: str = Field(..., description="ID returned by /api/analyze")
    vibeMatch: Optional[int] = Field(None, ge=1, le=5)
    itemsHelpful: Optional[bool] = None
    playlistMatch: Optional[bool] = None
    notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    ok: bool
    id: int


class HealthResponse(BaseModel):
    ok: bool
    prewarmed: bool
    pipeline_features: dict[str, bool]


# ---------- app factory ----------


def create_app(
    *,
    use_selection: bool = True,
    use_learned_classifier: bool = True,
    use_clip_classifier: Optional[bool] = None,
    with_playlist: bool = True,
    recommend_top_k: int = 10,
    playlist_top_k: int = 10,
    cors_origins: Optional[list[str]] = None,
) -> FastAPI:
    """Construct the FastAPI app. Pulled out so tests can build their own."""
    try:
        from vibecheck.vibe.clip_lora import get_default_classifier

        clip_available = get_default_classifier().is_available
    except Exception:
        clip_available = False

    state = {
        "prewarmed": False,
        "use_selection": use_selection,
        "use_learned_classifier": use_learned_classifier,
        "use_clip_classifier": use_clip_classifier,
        "clip_available": clip_available,
        "with_playlist": with_playlist,
        "recommend_top_k": recommend_top_k,
        "playlist_top_k": playlist_top_k,
    }

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        """Pre-warm heavy ML state once on startup so first request is fast.

        Failures here don't block boot -- the request handler will re-raise
        the same error path if/when it actually needs the encoder.
        """
        if os.getenv("VIBECHECK_SKIP_PREWARM") == "1":
            logger.info("pre-warm skipped by VIBECHECK_SKIP_PREWARM")
            yield
            return
        try:
            from vibecheck.rec.recommend import (
                _shared_encoder,
                _shared_product_index,
                _shared_reddit_index,
            )

            logger.info("pre-warming fashion-bert encoder + indexes...")
            _shared_encoder()
            _shared_reddit_index()
            _shared_product_index()
            state["prewarmed"] = True
            logger.info("pre-warm complete")
        except Exception as exc:  # noqa: BLE001 -- intentional broad catch
            logger.warning("pre-warm skipped: %s", exc)
        yield

    app = FastAPI(
        title="VibeCheck Backend",
        version="0.1.0",
        description="Backend for the VibeCheck Expo mobile app (CS 4701 demo).",
        lifespan=lifespan,
    )
    app.state.vibe_config = state

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            ok=True,
            prewarmed=bool(state["prewarmed"]),
            pipeline_features={
                "use_selection": state["use_selection"],
                "use_learned_classifier": state["use_learned_classifier"],
                "clip_classifier_available": state["clip_available"],
                "with_playlist": state["with_playlist"],
            },
        )

    @app.post("/api/analyze")
    async def analyze(
        mode: VibeMode = Form(...),
        photos: list[UploadFile] = File(...),
    ) -> dict:
        if not photos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one photo is required.",
            )
        if len(photos) > 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At most 6 photos allowed per request.",
            )

        image_bytes: list[bytes] = []
        for upload in photos:
            data = await upload.read()
            if not data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Empty photo upload: {upload.filename}",
                )
            image_bytes.append(data)

        try:
            result = analyze_images(
                image_bytes,
                mode=mode,
                with_recommendations=True,
                recommend_top_k=state["recommend_top_k"],
                use_selection=state["use_selection"],
                use_learned_classifier=state["use_learned_classifier"],
                use_clip_classifier=state["use_clip_classifier"],
                with_playlist=state["with_playlist"],
                playlist_top_k=state["playlist_top_k"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("analyze pipeline failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"pipeline error: {exc}",
            ) from exc

        # We don't echo the user's photos back -- the mobile client already has
        # the local URIs and the backend has no business storing them. Returning
        # an empty list keeps the contract simple, and the mobile screen falls
        # back to the URIs in its store.
        return map_result_to_vibe_check(result, photos=[], mode=mode)

    @app.post("/api/feedback", response_model=FeedbackResponse)
    async def feedback(body: FeedbackRequest) -> FeedbackResponse:
        try:
            row_id = record_feedback(
                vibe_check_id=body.vibeCheckId,
                vibe_match=body.vibeMatch,
                items_helpful=body.itemsHelpful,
                playlist_match=body.playlistMatch,
                extra={"notes": body.notes} if body.notes else None,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("feedback insert failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"feedback storage error: {exc}",
            ) from exc
        return FeedbackResponse(ok=True, id=row_id)

    return app


# Module-level instance for ``uvicorn vibecheck.server.app:app``. Reads the
# CORS origins from the env so deployments can lock down without code changes.
def _origins_from_env() -> list[str]:
    raw = os.getenv("VIBECHECK_CORS_ORIGINS", "*")
    if raw == "*" or not raw.strip():
        return ["*"]
    return [item.strip() for item in raw.split(",") if item.strip()]


app = create_app(cors_origins=_origins_from_env())
