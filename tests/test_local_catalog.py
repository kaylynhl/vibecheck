"""Tests for the local CSV-backed catalog client.

We construct tiny synthetic CSVs on disk rather than touching the real
168 MB Kaggle dataset. This keeps the suite fast and self-contained.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from vibecheck.rec.local_catalog import LocalCatalogClient
from vibecheck.schemas import ExtractedTag


def _write_catalog(path: Path, rows: list[dict]) -> Path:
    """Persist ``rows`` as a CSV with the columns the client expects."""
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return path


def _row(
    *,
    track_id: str,
    name: str,
    artist: str,
    genre: str = "pop",
    popularity: int = 50,
    danceability: float = 0.5,
    energy: float = 0.5,
    valence: float = 0.5,
    acousticness: float = 0.5,
    instrumentalness: float = 0.0,
    speechiness: float = 0.05,
    liveness: float = 0.1,
    loudness: float = -10.0,
    tempo: float = 110.0,
    key: int = 5,
    mode: int = 1,
) -> dict:
    return {
        "track_id": track_id,
        "track_name": name,
        "artist_name": artist,
        "genre": genre,
        "popularity": popularity,
        "year": 2020,
        "danceability": danceability,
        "energy": energy,
        "valence": valence,
        "acousticness": acousticness,
        "instrumentalness": instrumentalness,
        "speechiness": speechiness,
        "liveness": liveness,
        "loudness": loudness,
        "tempo": tempo,
        "key": key,
        "mode": mode,
    }


# ---- search_tracks (keyword) ------------------------------------------------


def test_search_tracks_substring_matches_track_name(tmp_path: Path) -> None:
    csv = _write_catalog(
        tmp_path / "c.csv",
        [
            _row(track_id="a", name="Wild Horses", artist="Stones"),
            _row(track_id="b", name="Heather", artist="Conan Gray"),
        ],
    )
    client = LocalCatalogClient(csv_path=csv)
    results = client.search_tracks("heather", limit=5)
    assert [r["id"] for r in results] == ["b"]
    # Returned dict must match Spotify's track JSON shape so normalize_track works.
    assert results[0]["external_urls"]["spotify"].endswith("/b")
    assert isinstance(results[0]["artists"], list)
    assert results[0]["artists"][0]["name"] == "Conan Gray"


def test_search_tracks_substring_matches_artist_or_genre(tmp_path: Path) -> None:
    csv = _write_catalog(
        tmp_path / "c.csv",
        [
            _row(track_id="a", name="Track A", artist="Phoebe Bridgers", genre="indie"),
            _row(track_id="b", name="Track B", artist="Hans Zimmer", genre="classical"),
        ],
    )
    client = LocalCatalogClient(csv_path=csv)
    assert {r["id"] for r in client.search_tracks("bridgers")} == {"a"}
    assert {r["id"] for r in client.search_tracks("classical")} == {"b"}


def test_search_tracks_is_case_insensitive(tmp_path: Path) -> None:
    csv = _write_catalog(
        tmp_path / "c.csv",
        [_row(track_id="a", name="Cardigan", artist="Taylor Swift")],
    )
    client = LocalCatalogClient(csv_path=csv)
    assert {r["id"] for r in client.search_tracks("TAYLOR")} == {"a"}
    assert {r["id"] for r in client.search_tracks("taylor")} == {"a"}


def test_search_tracks_orders_by_popularity_desc(tmp_path: Path) -> None:
    csv = _write_catalog(
        tmp_path / "c.csv",
        [
            _row(track_id="low", name="Folk Song", artist="Whoever", popularity=20),
            _row(track_id="high", name="Folk Hit", artist="Whoever", popularity=90),
            _row(track_id="mid", name="Folk Cover", artist="Whoever", popularity=55),
        ],
    )
    client = LocalCatalogClient(csv_path=csv)
    ids = [r["id"] for r in client.search_tracks("folk", limit=3)]
    assert ids == ["high", "mid", "low"]


def test_search_tracks_returns_empty_for_no_match(tmp_path: Path) -> None:
    csv = _write_catalog(
        tmp_path / "c.csv",
        [_row(track_id="a", name="Anything", artist="Someone")],
    )
    client = LocalCatalogClient(csv_path=csv)
    assert client.search_tracks("nonexistent") == []


def test_search_tracks_empty_query_returns_empty(tmp_path: Path) -> None:
    csv = _write_catalog(
        tmp_path / "c.csv",
        [_row(track_id="a", name="x", artist="y")],
    )
    client = LocalCatalogClient(csv_path=csv)
    assert client.search_tracks("") == []
    assert client.search_tracks("   ") == []


def test_search_tracks_attaches_audio_features(tmp_path: Path) -> None:
    csv = _write_catalog(
        tmp_path / "c.csv",
        [_row(track_id="a", name="Track", artist="Artist", valence=0.42, energy=0.31)],
    )
    client = LocalCatalogClient(csv_path=csv)
    result = client.search_tracks("track")[0]
    assert result["audio_features"]["valence"] == 0.42
    assert result["audio_features"]["energy"] == 0.31


# ---- search_by_aesthetic (audio filter) -------------------------------------


def test_search_by_aesthetic_promotes_profile_matching_tracks(
    tmp_path: Path,
) -> None:
    """dark_academia profile favours low valence + low energy + high acousticness.
    The audio filter must return such a track ahead of an EDM-shaped one."""
    csv = _write_catalog(
        tmp_path / "c.csv",
        [
            _row(
                track_id="moody",
                name="Quiet Library",
                artist="Anon",
                valence=0.20,
                energy=0.30,
                acousticness=0.85,
                instrumentalness=0.75,
                danceability=0.30,
                tempo=90.0,
            ),
            _row(
                track_id="bumping",
                name="Club Banger",
                artist="DJ",
                valence=0.95,
                energy=0.95,
                acousticness=0.05,
                instrumentalness=0.0,
                danceability=0.85,
                tempo=140.0,
            ),
        ],
    )
    client = LocalCatalogClient(csv_path=csv)
    results = client.search_by_aesthetic("dark_academia", limit=2, popularity_floor=0)
    assert [r["id"] for r in results] == ["moody", "bumping"]


def test_search_by_aesthetic_returns_empty_for_unknown_aesthetic(
    tmp_path: Path,
) -> None:
    csv = _write_catalog(
        tmp_path / "c.csv",
        [_row(track_id="a", name="x", artist="y")],
    )
    client = LocalCatalogClient(csv_path=csv)
    assert client.search_by_aesthetic("not_a_real_vibe") == []


def test_search_by_aesthetic_applies_visual_tag_nudges(tmp_path: Path) -> None:
    """A 'dim' lighting tag lowers the dark_academia valence target. We
    construct two rows that match the base profile on every feature *except*
    valence so the nudge effect is observable in isolation: ``base_top``
    matches the un-nudged valence target, ``dim_top`` matches the nudged one."""
    # All features below are set to dark_academia's exact profile targets;
    # only valence differs between the two tracks. That isolates the nudge.
    common = dict(
        energy=0.35,
        acousticness=0.75,
        instrumentalness=0.70,
        danceability=0.35,
        tempo=95.0,
    )
    csv = _write_catalog(
        tmp_path / "c.csv",
        [
            _row(track_id="base_top", name="A", artist="A", valence=0.25, **common),
            _row(track_id="dim_top", name="B", artist="B", valence=0.15, **common),
        ],
    )
    client = LocalCatalogClient(csv_path=csv)

    base = client.search_by_aesthetic("dark_academia", limit=2, popularity_floor=0)
    nudged = client.search_by_aesthetic(
        "dark_academia",
        limit=2,
        popularity_floor=0,
        image_tags=[
            ExtractedTag(category="lighting", value="dim", confidence=1.0, evidence="")
        ],
    )

    # Un-nudged: base profile valence target is 0.25 -> base_top wins.
    assert base[0]["id"] == "base_top"
    # After dim-lighting nudge: valence target drops to ~0.15 -> dim_top wins.
    assert nudged[0]["id"] == "dim_top"


def test_search_by_aesthetic_respects_popularity_floor(tmp_path: Path) -> None:
    csv = _write_catalog(
        tmp_path / "c.csv",
        [
            _row(
                track_id="unpopular_perfect",
                name="Hidden Gem",
                artist="Obscure",
                popularity=5,
                valence=0.25,
                energy=0.35,
                acousticness=0.75,
                instrumentalness=0.70,
            ),
            _row(
                track_id="popular_decent",
                name="Big Hit",
                artist="Famous",
                popularity=80,
                valence=0.40,
                energy=0.45,
                acousticness=0.50,
                instrumentalness=0.20,
            ),
        ],
    )
    client = LocalCatalogClient(csv_path=csv)
    results = client.search_by_aesthetic("dark_academia", limit=5, popularity_floor=30)
    assert [r["id"] for r in results] == ["popular_decent"]


# ---- error handling ---------------------------------------------------------


def test_missing_csv_raises_helpful_error(tmp_path: Path) -> None:
    import pytest

    client = LocalCatalogClient(csv_path=tmp_path / "does_not_exist.csv")
    with pytest.raises(FileNotFoundError, match="Spotify catalog CSV"):
        client.search_tracks("anything")
