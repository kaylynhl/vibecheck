"""End-to-end tests for the FastAPI backend (Step 8).

We monkeypatch ``vibecheck.server.app.analyze_images`` so the test never hits
Groq, FAISS, sentence-transformers, or Spotify. The mappers and the HTTP
plumbing are what we're testing here.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vibecheck import server as server_pkg
from vibecheck.schemas import (
    DebugInfo,
    ExtractedTag,
    VibeAnalysisResult,
    VibeScore,
)
from vibecheck.server import storage as server_storage
from vibecheck.server.app import create_app


def _make_fake_result() -> VibeAnalysisResult:
    """Build a realistic-looking pipeline result without running the pipeline."""
    return VibeAnalysisResult(
        raw_description="A cozy cottagecore-leaning interior.",
        extracted_tags=[
            ExtractedTag(category="palette", value="warm neutrals", confidence=0.9, evidence="warm neutrals"),
            ExtractedTag(category="texture", value="woven", confidence=0.7, evidence="woven baskets"),
            ExtractedTag(category="pattern", value="floral", confidence=0.6, evidence="floral patterns"),
        ],
        vibe_scores=[
            VibeScore(vibe="cottagecore", score=0.78, matched_keywords=["floral"], description=""),
            VibeScore(vibe="minimalist", score=0.12, matched_keywords=[], description=""),
        ],
        top_vibes=[
            VibeScore(vibe="cottagecore", score=0.78, matched_keywords=["floral"], description=""),
            VibeScore(vibe="minimalist", score=0.12, matched_keywords=[], description=""),
        ],
        confidence_notes=["test note"],
        debug=DebugInfo(
            input_count=1,
            input_kinds=["image/jpeg"],
            model="stub-model",
            timings_ms={"vision_description": 12},
            warnings=[],
            scene_type="room",
            validation_passed=True,
        ),
        item_recommendations=[
            {
                "id": "p1",
                "name": "Linen Throw Pillow",
                "category": "throw pillow",
                "brand": "ExampleBrand",
                "gender": "unisex",
                "price": "$22",
                "image_url": "https://example.com/p1.jpg",
                "product_url": "https://example.com/p1",
                "score": 0.81,
            },
            {
                "id": "p2",
                "name": "Sage Linen Curtains",
                "category": "curtains",
                "brand": "",
                "gender": "",
                "price": "$45",
                "image_url": "https://example.com/p2.jpg",
                "product_url": "https://example.com/p2",
                "score": 1.5,  # > 1 -> exercises the squash branch
            },
        ],
        playlist_recommendations=[
            {
                "spotify_id": "t1",
                "name": "Floral",
                "artists": ["Indie Artist", "Other"],
                "album_name": "Album",
                "album_image": "https://example.com/album.jpg",
                "preview_url": "https://example.com/preview.mp3",
                "spotify_url": "https://open.spotify.com/track/t1",
                "duration_ms": 215000,
                "score": 0.62,
            },
        ],
    )


def _build_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tmp_path: Path,
    fake_result: VibeAnalysisResult | None = None,
) -> TestClient:
    """Construct a TestClient with the pipeline + feedback DB stubbed."""
    fake_result = fake_result or _make_fake_result()

    captured: dict[str, object] = {}

    def fake_analyze_images(inputs, **kwargs):
        captured["inputs"] = list(inputs)
        captured["kwargs"] = kwargs
        return fake_result

    monkeypatch.setattr(
        "vibecheck.server.app.analyze_images", fake_analyze_images
    )
    monkeypatch.setattr(
        server_storage,
        "DEFAULT_FEEDBACK_DB",
        tmp_path / "feedback.sqlite",
    )

    app = create_app()
    client = TestClient(app)
    client.captured = captured  # type: ignore[attr-defined]
    return client


# ---------- /api/health ----------


def test_health_returns_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    client = _build_client(monkeypatch, tmp_path=tmp_path)
    with client:
        response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "pipeline_features" in body
    assert set(body["pipeline_features"]) == {
        "use_selection",
        "use_learned_classifier",
        "with_playlist",
    }


# ---------- /api/analyze ----------


def test_analyze_returns_mobile_shaped_vibe_check(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client = _build_client(monkeypatch, tmp_path=tmp_path)

    response = client.post(
        "/api/analyze",
        data={"mode": "room"},
        files={"photos": ("front.jpg", io.BytesIO(b"\xff\xd8\xff fake jpeg"), "image/jpeg")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) >= {
        "id",
        "photos",
        "mode",
        "tags",
        "vibes",
        "itemRecommendations",
        "playlistRecommendation",
        "createdAt",
    }
    assert body["mode"] == "room"
    assert body["id"].startswith("vibe-")
    assert all({"id", "category", "value", "confidence"} <= set(t) for t in body["tags"])
    assert body["vibes"][0]["aesthetic"] == "cottagecore"
    assert 0.0 <= body["vibes"][0]["confidence"] <= 1.0

    item = body["itemRecommendations"][0]
    assert {"id", "name", "imageUrl", "matchScore", "category"} <= set(item)
    assert 0.0 <= item["matchScore"] <= 1.0  # squashed even for raw score > 1

    playlist = body["playlistRecommendation"]
    assert playlist["tracks"][0]["artist"] == "Indie Artist, Other"
    assert playlist["coverImage"] == "https://example.com/album.jpg"
    assert playlist["aesthetic"] == "cottagecore"


def test_analyze_forwards_kwargs_to_pipeline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client = _build_client(monkeypatch, tmp_path=tmp_path)

    response = client.post(
        "/api/analyze",
        data={"mode": "outfit"},
        files=[
            ("photos", ("a.jpg", io.BytesIO(b"a" * 8), "image/jpeg")),
            ("photos", ("b.jpg", io.BytesIO(b"b" * 8), "image/jpeg")),
        ],
    )

    assert response.status_code == 200
    captured = client.captured  # type: ignore[attr-defined]
    assert len(captured["inputs"]) == 2
    kwargs = captured["kwargs"]
    assert kwargs["mode"] == "outfit"
    assert kwargs["with_recommendations"] is True
    assert kwargs["with_playlist"] is True
    assert kwargs["use_selection"] is True
    assert kwargs["use_learned_classifier"] is True


def test_analyze_rejects_zero_photos(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client = _build_client(monkeypatch, tmp_path=tmp_path)
    # FastAPI itself returns 422 when the `photos` form field is missing -- a
    # cleaner contract than us returning 400 for the same case.
    response = client.post("/api/analyze", data={"mode": "room"})
    assert response.status_code in (400, 422)


def test_analyze_rejects_too_many_photos(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client = _build_client(monkeypatch, tmp_path=tmp_path)
    files = [
        ("photos", (f"p{i}.jpg", io.BytesIO(b"x" * 8), "image/jpeg"))
        for i in range(7)
    ]
    response = client.post("/api/analyze", data={"mode": "room"}, files=files)
    assert response.status_code == 400


def test_analyze_returns_502_on_pipeline_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("groq melted")

    monkeypatch.setattr("vibecheck.server.app.analyze_images", boom)
    monkeypatch.setattr(
        server_storage,
        "DEFAULT_FEEDBACK_DB",
        tmp_path / "feedback.sqlite",
    )
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/analyze",
        data={"mode": "room"},
        files={"photos": ("a.jpg", io.BytesIO(b"a"), "image/jpeg")},
    )
    assert response.status_code == 502
    assert "groq melted" in response.json()["detail"]


# ---------- /api/feedback ----------


def test_feedback_round_trips_through_sqlite(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client = _build_client(monkeypatch, tmp_path=tmp_path)

    response = client.post(
        "/api/feedback",
        json={
            "vibeCheckId": "vibe-abc",
            "vibeMatch": 5,
            "itemsHelpful": True,
            "playlistMatch": False,
            "notes": "items were spot on, music was meh",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["id"] >= 1

    rows = server_storage.list_feedback(db_path=tmp_path / "feedback.sqlite")
    assert len(rows) == 1
    row = rows[0]
    assert row["vibe_check_id"] == "vibe-abc"
    assert row["vibe_match"] == 5
    assert row["items_helpful"] is True
    assert row["playlist_match"] is False
    assert row["extra"] == {"notes": "items were spot on, music was meh"}


def test_feedback_rejects_out_of_range_rating(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client = _build_client(monkeypatch, tmp_path=tmp_path)
    response = client.post(
        "/api/feedback",
        json={"vibeCheckId": "vibe-x", "vibeMatch": 10},
    )
    assert response.status_code == 422


def test_package_exports_app() -> None:
    """`from vibecheck.server import app` should give the FastAPI instance."""
    assert hasattr(server_pkg, "app")
    assert hasattr(server_pkg, "create_app")
