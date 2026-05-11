"""Map pipeline outputs into the JSON shape the mobile ``VibeCheck`` expects.

The mobile app (``mobile/services/types.ts``) has a closed schema:

    VibeCheck {
        id, photos, mode, tags[], vibes[],
        itemRecommendations[], playlistRecommendation, createdAt,
    }

The Python pipeline returns its own dataclass-flavoured shape (see
``vibecheck.schemas``). Keep all reshaping in this one file so the server route
stays a thin HTTP wrapper and the mobile app never has to know about backend
internals.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

from vibecheck.schemas import VibeAnalysisResult
from vibecheck.tags.vocabulary import TAG_CATEGORIES

_DESCRIPTION_BY_VIBE: dict[str, str] = {
    "cottagecore": "Soft, pastoral, vintage — floral patterns and warm naturals.",
    "minimalist": "Pared-back, calm, functional — neutral palette and clean lines.",
    "y2k": "Late-90s/early-2000s nostalgia — playful tech, glossy colour, low-rise cuts.",
    "dark academia": "Moody, scholarly, autumnal — tweeds, leather, candlelight.",
    "streetwear": "Hype-driven casual — sneakers, hoodies, graphic prints.",
    "coquette": "Hyper-feminine, ribbons-and-lace, soft pinks and bows.",
    "old money": "Quiet wealth — cashmere, neutrals, polished restraint.",
    "cyberpunk": "Neon-on-black, tech-wear, dystopian sheen.",
    "boho": "Eclectic, layered, earthy — global textiles and warm tones.",
    "grunge": "Distressed, dark, 90s alt-rock — flannels and combat boots.",
    "scandinavian": "Bright, functional, woody — hygge minimalism.",
    "industrial": "Raw, mechanical — exposed brick, metal, concrete.",
    "vintage": "Pulled-from-another-decade pieces with patina and character.",
    "preppy": "Polished casual — collars, pleats, varsity heritage.",
    "kawaii": "Cute-maximalism — pastels, plushies, character motifs.",
}


def map_result_to_vibe_check(
    result: VibeAnalysisResult,
    *,
    photos: list[str],
    mode: str,
    vibe_check_id: str | None = None,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Return a JSON-safe dict that satisfies the mobile ``VibeCheck`` type."""
    primary_vibe = result.top_vibes[0].vibe if result.top_vibes else None

    return {
        "id": vibe_check_id or _generate_id(),
        "photos": photos,
        "mode": mode,
        "tags": list(_map_tags(result.extracted_tags)),
        "vibes": list(_map_vibes(result.top_vibes)),
        "itemRecommendations": list(_map_items(result.item_recommendations)),
        "playlistRecommendation": _map_playlist(
            result.playlist_recommendations, aesthetic=primary_vibe or "your vibe"
        ),
        "createdAt": (created_at or datetime.now(timezone.utc)).isoformat(),
        "debug": _map_debug(result),
    }


def _map_tags(extracted_tags: Iterable[Any]) -> Iterable[dict[str, Any]]:
    """Mobile ``Tag``: { id, category, value, confidence }.

    Mobile's ``TagCategory`` enum is the same six categories as our backend
    vocabulary, so anything outside that set is silently dropped to keep the
    mobile type contract honest.
    """
    valid = set(TAG_CATEGORIES)
    for idx, tag in enumerate(extracted_tags):
        if tag.category not in valid:
            continue
        yield {
            "id": f"tag-{idx}-{_slug(tag.category)}-{_slug(tag.value)}",
            "category": tag.category,
            "value": tag.value,
            "confidence": float(tag.confidence),
        }


def _map_vibes(top_vibes: Iterable[Any]) -> Iterable[dict[str, Any]]:
    """Mobile ``VibeResult``: { aesthetic, confidence, description? }."""
    for vibe in top_vibes:
        confidence = _normalise_score(vibe.score)
        description = (
            vibe.description
            or _DESCRIPTION_BY_VIBE.get(vibe.vibe)
        )
        yield {
            "aesthetic": vibe.vibe,
            "confidence": confidence,
            "description": description,
        }


def _map_items(items: list[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    """Mobile ``Item``: { id, name, imageUrl, tags[], matchScore, category, price?, source? }.

    Pipeline ``recommend_items`` returns ``Product.to_dict(score=...)`` which
    uses snake_case (``image_url``, ``product_url``) and includes some fields
    the mobile app doesn't use; reshape to camelCase + the mobile contract.
    """
    for raw in items:
        product_category = (raw.get("category") or "").lower()
        mobile_category = _coerce_item_category(product_category)
        score = raw.get("score")
        match_score = _normalise_score(float(score)) if score is not None else 0.0

        tag_strings: list[str] = []
        if isinstance(raw.get("brand"), str) and raw["brand"]:
            tag_strings.append(raw["brand"])
        if product_category:
            tag_strings.append(product_category)

        yield {
            "id": str(raw.get("id") or _generate_id()),
            "name": str(raw.get("name") or "Untitled item"),
            "imageUrl": str(raw.get("image_url") or raw.get("imageUrl") or ""),
            "tags": tag_strings,
            "matchScore": match_score,
            "category": mobile_category,
            "price": raw.get("price") or None,
            "source": raw.get("source") or "Depop",
            "productUrl": raw.get("product_url") or raw.get("productUrl"),
        }


def _map_playlist(
    tracks: list[dict[str, Any]], *, aesthetic: str
) -> dict[str, Any]:
    """Mobile ``Playlist``: { id, name, tracks, aesthetic, coverImage? }.

    We wrap the ranked list of Spotify tracks (Step 5) into a single
    synthetic playlist object -- the app renders one playlist card per result.
    """
    mapped_tracks = [_map_track(t) for t in tracks]
    cover = next(
        (t["albumArt"] for t in mapped_tracks if t.get("albumArt")),
        None,
    )
    return {
        "id": f"vibe-playlist-{_slug(aesthetic)}-{_generate_id(short=True)}",
        "name": f"{aesthetic.title()} Playlist".strip(),
        "tracks": mapped_tracks,
        "aesthetic": aesthetic,
        "coverImage": cover,
    }


def _map_track(track: dict[str, Any]) -> dict[str, Any]:
    """Mobile ``Track``: { id, name, artist, albumArt?, previewUrl?, durationMs? }."""
    artists = track.get("artists") or []
    if isinstance(artists, list):
        artist = ", ".join(str(a) for a in artists if a)
    else:
        artist = str(artists)
    return {
        "id": str(track.get("spotify_id") or _generate_id()),
        "name": str(track.get("name") or "Untitled track"),
        "artist": artist or "Unknown artist",
        "albumArt": track.get("album_image"),
        "previewUrl": track.get("preview_url"),
        "durationMs": track.get("duration_ms"),
        "spotifyUrl": track.get("spotify_url"),
    }


def _map_debug(result: VibeAnalysisResult) -> dict[str, Any]:
    debug = result.debug.to_dict()
    debug["confidence_notes"] = list(result.confidence_notes)
    return debug


def _normalise_score(score: float) -> float:
    """Squash a (potentially uncalibrated) score into [0, 1] for UI display.

    Pipeline scores have varying provenance:
        * fashion-bert cosine -> already in [-1, 1], typically [0, 0.8]
        * hand-weighted vibe scoring -> raw sums, can be >> 1
        * learned classifier -> probability in [0, 1]
    We clamp negatives to 0 and squash > 1 with x / (1 + x) so the % match
    badge never reports nonsensical values like 250%.
    """
    if score is None:
        return 0.0
    if score < 0:
        return 0.0
    if score > 1:
        return float(score / (1.0 + score))
    return float(score)


def _coerce_item_category(raw: str) -> str:
    """Map free-form product categories onto the mobile Item.category union.

    Mobile expects one of: furniture | decor | clothing | accessory.
    """
    raw = (raw or "").lower()
    if any(k in raw for k in ("sofa", "chair", "table", "desk", "bed", "shelf",
                              "furniture", "lamp")):
        return "furniture"
    if any(k in raw for k in ("rug", "pillow", "art", "poster", "plant",
                              "vase", "throw", "decor", "candle")):
        return "decor"
    if any(k in raw for k in ("bag", "hat", "scarf", "belt", "jewelry", "watch",
                              "sunglasses", "accessory", "accessories")):
        return "accessory"
    return "clothing"


def _slug(value: str) -> str:
    out = re.sub(r"[^a-zA-Z0-9]+", "-", value or "").strip("-").lower()
    return out or "x"


def _generate_id(short: bool = False) -> str:
    raw = uuid.uuid4().hex
    return raw[:8] if short else f"vibe-{raw[:12]}"
