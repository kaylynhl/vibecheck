"""Backend-owned catalog of supported vibes and their keyword profiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModeBias = Literal["room", "outfit", "both"]


@dataclass(frozen=True)
class VibeProfile:
    """Weighted keyword profile for one supported aesthetic."""

    name: str
    description: str
    mode_bias: ModeBias
    keyword_weights: dict[str, float]


VIBE_PROFILES: tuple[VibeProfile, ...] = (
    VibeProfile(
        name="cottagecore",
        description="Romanticized rural life with soft, natural elements and vintage charm.",
        mode_bias="both",
        keyword_weights={
            "warm neutrals": 1.0,
            "sage green": 1.0,
            "cozy": 1.1,
            "woven": 0.9,
            "floral": 1.0,
            "wood": 0.9,
            "natural fibers": 0.9,
            "flowy": 0.8,
        },
    ),
    VibeProfile(
        name="dark academia",
        description="Scholarly, moody, and vintage with rich tones and classic materials.",
        mode_bias="both",
        keyword_weights={
            "dark and moody": 1.1,
            "earth tones": 1.0,
            "moody": 1.0,
            "rich": 0.9,
            "plaid": 0.8,
            "leather": 1.0,
            "wood": 0.8,
            "tailored": 0.7,
        },
    ),
    VibeProfile(
        name="minimalist",
        description="Clean lines, restrained palettes, and intentional simplicity.",
        mode_bias="both",
        keyword_weights={
            "cool neutrals": 1.0,
            "monochromatic": 0.9,
            "minimal": 1.1,
            "smooth": 0.9,
            "solid": 0.8,
            "streamlined": 0.9,
            "natural": 0.6,
            "glass": 0.7,
        },
    ),
    VibeProfile(
        name="y2k",
        description="Early-2000s nostalgia with playful shine and pop styling.",
        mode_bias="outfit",
        keyword_weights={
            "vibrant": 0.9,
            "high contrast": 0.8,
            "metal": 0.8,
            "chrome": 1.0,
            "cropped": 0.9,
            "fitted": 0.8,
            "synthetic": 0.7,
        },
    ),
    VibeProfile(
        name="coastal grandmother",
        description="Relaxed, breezy elegance with airy neutrals and soft natural textures.",
        mode_bias="both",
        keyword_weights={
            "light and airy": 1.0,
            "warm neutrals": 0.9,
            "linen": 1.0,
            "natural fibers": 0.9,
            "relaxed": 0.8,
            "soft": 0.7,
            "wood": 0.6,
        },
    ),
    VibeProfile(
        name="indie sleaze",
        description="Messy nightlife cool with high contrast, distressed pieces, and layered styling.",
        mode_bias="outfit",
        keyword_weights={
            "high contrast": 1.0,
            "black and white": 0.9,
            "harsh": 0.8,
            "distressed": 1.1,
            "leather": 0.9,
            "animal print": 0.7,
            "layered": 0.9,
            "fitted": 0.7,
        },
    ),
    VibeProfile(
        name="clean girl",
        description="Fresh, polished minimalism with sleek silhouettes and natural light.",
        mode_bias="outfit",
        keyword_weights={
            "cool neutrals": 0.9,
            "cream": 0.8,
            "natural": 0.8,
            "smooth": 1.0,
            "sleek": 1.0,
            "solid": 0.8,
            "fitted": 0.9,
            "streamlined": 0.8,
        },
    ),
    VibeProfile(
        name="cyberpunk",
        description="Futuristic urban grit with neon, contrast, and synthetic shine.",
        mode_bias="both",
        keyword_weights={
            "neon": 1.2,
            "high contrast": 1.0,
            "dark and moody": 0.8,
            "metal": 0.8,
            "chrome": 0.9,
            "synthetic": 0.9,
            "structured": 0.7,
        },
    ),
    VibeProfile(
        name="bohemian",
        description="Free-spirited layering with natural materials and eclectic pattern.",
        mode_bias="both",
        keyword_weights={
            "earth tones": 0.9,
            "layered": 1.0,
            "woven": 0.9,
            "flowy": 0.9,
            "paisley": 0.8,
            "floral": 0.7,
            "natural fibers": 0.8,
            "relaxed": 0.8,
        },
    ),
    VibeProfile(
        name="old money",
        description="Quiet luxury with classic silhouettes, polished materials, and restraint.",
        mode_bias="outfit",
        keyword_weights={
            "cream": 0.8,
            "tailored": 1.0,
            "structured": 0.9,
            "polished": 1.0,
            "silk": 0.9,
            "leather": 0.7,
            "monochromatic": 0.7,
        },
    ),
    VibeProfile(
        name="grunge",
        description="Raw, rebellious 90s styling with distressed textures and darker contrast.",
        mode_bias="outfit",
        keyword_weights={
            "dark and moody": 0.8,
            "distressed": 1.1,
            "plaid": 0.9,
            "denim": 0.9,
            "layered": 0.8,
            "oversized": 0.8,
            "black and white": 0.6,
        },
    ),
    VibeProfile(
        name="soft girl",
        description="Youthful and feminine with pastel palettes and gentle textures.",
        mode_bias="outfit",
        keyword_weights={
            "pastels": 1.1,
            "soft": 0.9,
            "plush": 0.8,
            "flowy": 0.8,
            "fitted": 0.6,
            "floral": 0.7,
        },
    ),
    VibeProfile(
        name="goblincore",
        description="Nature-forward, earthy, and a little chaotic with mossy, rustic appeal.",
        mode_bias="both",
        keyword_weights={
            "earth tones": 1.0,
            "rustic": 1.0,
            "wood": 0.9,
            "woven": 0.8,
            "natural fibers": 0.8,
            "rough": 0.8,
        },
    ),
    VibeProfile(
        name="light academia",
        description="A softer, brighter scholarly look with cream tones and tailored calm.",
        mode_bias="both",
        keyword_weights={
            "light and airy": 0.9,
            "cream": 0.9,
            "warm": 0.7,
            "tailored": 0.8,
            "wood": 0.6,
            "linen": 0.7,
            "natural": 0.7,
        },
    ),
    VibeProfile(
        name="streetwear",
        description="Urban, graphic, and relaxed with strong silhouettes and layered pieces.",
        mode_bias="outfit",
        keyword_weights={
            "high contrast": 0.8,
            "oversized": 1.0,
            "layered": 0.9,
            "structured": 0.6,
            "denim": 0.7,
            "camo": 0.7,
            "synthetic": 0.6,
        },
    ),
    VibeProfile(
        name="mid-century modern",
        description="Warm modernism with clean shapes, wood tones, and sculptural restraint.",
        mode_bias="room",
        keyword_weights={
            "warm neutrals": 0.8,
            "wood": 1.0,
            "structured": 0.9,
            "streamlined": 0.8,
            "smooth": 0.7,
            "glass": 0.6,
        },
    ),
    VibeProfile(
        name="scandinavian",
        description="Nordic calm with airy neutrals, wood, and cozy simplicity.",
        mode_bias="room",
        keyword_weights={
            "light and airy": 1.0,
            "cool neutrals": 0.8,
            "wood": 0.9,
            "cozy": 0.8,
            "minimal": 0.9,
            "natural": 0.7,
        },
    ),
    VibeProfile(
        name="industrial",
        description="Raw urban interior style with exposed materials and darker contrast.",
        mode_bias="room",
        keyword_weights={
            "dark and moody": 0.8,
            "metal": 1.0,
            "concrete": 1.0,
            "rough": 0.9,
            "structured": 0.7,
            "dramatic shadows": 0.6,
        },
    ),
    VibeProfile(
        name="maximalist",
        description="More-is-more styling with bold color, rich layering, and visual density.",
        mode_bias="both",
        keyword_weights={
            "vibrant": 1.0,
            "jewel tones": 0.9,
            "layered": 1.0,
            "rich": 0.9,
            "geometric": 0.6,
            "floral": 0.6,
            "voluminous": 0.7,
        },
    ),
    VibeProfile(
        name="japandi",
        description="Quiet fusion of Japanese and Scandinavian minimalism with natural materials.",
        mode_bias="room",
        keyword_weights={
            "warm neutrals": 0.8,
            "minimal": 1.0,
            "wood": 0.9,
            "natural fibers": 0.8,
            "streamlined": 0.8,
            "soft": 0.6,
        },
    ),
)
