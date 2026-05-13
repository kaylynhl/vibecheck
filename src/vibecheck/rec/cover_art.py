"""Generated playlist cover art via Pollinations.ai.

Pollinations is a free, no-auth SDXL/Flux frontend. The trick is that we don't
have to fetch or host anything ourselves -- the URL itself *is* the image, so
we just return it and let the mobile ``<Image>`` component request it on
demand. Pollinations caches each (prompt, seed, size) combination on its CDN,
so identical vibes hit a warm cache after the first request.

Prompts are deliberately abstract: no text on the image (Pollinations bakes in
arbitrary glyphs otherwise), square aspect, "no logo" flag set. Each vibe gets
a deterministic seed derived from its name so the same aesthetic always
produces the same cover during a demo.

Failure mode: if anything goes wrong (offline, opted out, URL too long) we
return ``None`` and ``mappers.py`` falls back to the first track's album art.
"""

from __future__ import annotations

import hashlib
import os
import urllib.parse
from functools import lru_cache

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"
DEFAULT_MODEL = "flux"
DEFAULT_SIZE = 512

VIBE_PROMPT_STYLE: dict[str, str] = {
    "cottagecore": "wildflower meadow at golden hour, soft pastel tones, vintage botanical",
    "minimalist": "single ceramic vase, white background, soft shadows, negative space",
    "y2k": "early 2000s glossy iridescent bubbles, chrome lettering avoided, cyber-pink",
    "dark academia": "old library candlelight, leather books, autumn moodboard",
    "streetwear": "concrete and graffiti texture, neon highlights, urban photograph",
    "coquette": "silk ribbon, pearls, pale pink florals, soft-focus film",
    "old money": "mahogany interior, brass fixtures, navy and cream palette",
    "cyberpunk": "neon street reflection in puddles, rain, magenta cyan glow",
    "boho": "macrame, terracotta pottery, warm earth tones, layered textiles",
    "grunge": "torn denim, faded flannel, distressed darkroom film grain",
    "scandinavian": "blonde wood, white walls, single green plant, soft daylight",
    "industrial": "exposed brick, edison bulbs, concrete and matte metal",
    "vintage": "1970s polaroid, warm fade, dust grain, retro color palette",
    "preppy": "argyle pattern, polished oxford shoes, ivy league campus",
    "kawaii": "pastel plush toys, sparkles, bubblegum pink, dreamy soft focus",
}

DEFAULT_PROMPT_SUFFIX = (
    "album cover art, square composition, atmospheric, painterly, no text, "
    "no letters, no watermark, high quality"
)


def _vibe_prompt(vibe: str) -> str:
    style = VIBE_PROMPT_STYLE.get(
        vibe.lower(),
        f"{vibe} aesthetic mood, evocative imagery",
    )
    return f"{style}, {DEFAULT_PROMPT_SUFFIX}"


def _vibe_seed(vibe: str) -> int:
    """Deterministic seed per vibe so the same aesthetic always gets the same
    cover during a demo (Pollinations honours the seed param)."""
    h = hashlib.sha1(vibe.lower().encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 2_000_000_000


@lru_cache(maxsize=128)
def cover_url_for_vibe(vibe: str, size: int = DEFAULT_SIZE) -> str | None:
    """Return a Pollinations image URL for ``vibe``, or ``None`` if disabled.

    The function is cached -- repeated calls with the same vibe return the
    same URL, which keeps Pollinations' own CDN warm.
    """
    if os.environ.get("VIBECHECK_DISABLE_COVER_ART") == "1":
        return None
    if not vibe:
        return None

    prompt = _vibe_prompt(vibe)
    encoded = urllib.parse.quote(prompt, safe="")
    seed = _vibe_seed(vibe)
    params = urllib.parse.urlencode(
        {
            "width": size,
            "height": size,
            "seed": seed,
            "model": DEFAULT_MODEL,
            "nologo": "true",
            "enhance": "true",
        }
    )
    return f"{POLLINATIONS_BASE}/{encoded}?{params}"
