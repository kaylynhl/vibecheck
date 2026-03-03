import type { VibeResult } from "../services/types";

export const AESTHETIC_DESCRIPTIONS: Record<string, string> = {
  cottagecore:
    "Romanticized rural life with soft, natural elements and vintage charm",
  "dark academia":
    "Gothic, scholarly aesthetic with rich browns, old books, and intellectual vibes",
  minimalist:
    "Clean lines, neutral colors, and intentional simplicity with purposeful space",
  y2k: "Early 2000s nostalgia with metallics, low-rise, and cyber-futuristic elements",
  "coastal grandmother":
    "Relaxed, breezy elegance inspired by Nancy Meyers films and seaside living",
  "indie sleaze":
    "Messy, effortless cool with vintage finds, band tees, and nightlife energy",
  "clean girl":
    "Fresh, dewy, natural beauty with slicked hair and minimal makeup",
  cyberpunk:
    "Neon-lit, dystopian futurism with tech elements and urban grit",
  bohemian:
    "Free-spirited, eclectic mix of patterns, textures, and global influences",
  "old money":
    "Timeless, understated luxury with quality fabrics and classic silhouettes",
  grunge: "Raw, rebellious 90s aesthetic with flannel, distressed denim, and band merch",
  "soft girl":
    "Youthful, feminine aesthetic with pastels, blush tones, and cute accessories",
  goblincore:
    "Appreciation for the overlooked and unconventional in nature",
  "light academia":
    "Softer take on dark academia with cream tones and classical art appreciation",
  streetwear:
    "Urban fashion culture with sneakers, graphics, and brand collaborations",
  "mid-century modern":
    "1950s-60s design with clean lines, organic curves, and functional beauty",
  scandinavian:
    "Nordic-inspired minimalism with hygge comfort and natural materials",
  industrial:
    "Raw, unfinished aesthetic with exposed brick, metal, and urban edge",
  maximalist:
    "Bold, layered, more-is-more approach with rich colors and patterns",
  japandi:
    "Japanese-Scandinavian fusion balancing wabi-sabi with Nordic simplicity",
};

export const mockVibeResults: Record<string, VibeResult[]> = {
  room_cozy: [
    { aesthetic: "cottagecore", confidence: 0.85, description: AESTHETIC_DESCRIPTIONS.cottagecore },
    { aesthetic: "bohemian", confidence: 0.62, description: AESTHETIC_DESCRIPTIONS.bohemian },
    { aesthetic: "scandinavian", confidence: 0.45, description: AESTHETIC_DESCRIPTIONS.scandinavian },
  ],
  room_modern: [
    { aesthetic: "minimalist", confidence: 0.92, description: AESTHETIC_DESCRIPTIONS.minimalist },
    { aesthetic: "mid-century modern", confidence: 0.78, description: AESTHETIC_DESCRIPTIONS["mid-century modern"] },
    { aesthetic: "japandi", confidence: 0.55, description: AESTHETIC_DESCRIPTIONS.japandi },
  ],
  room_dark: [
    { aesthetic: "dark academia", confidence: 0.88, description: AESTHETIC_DESCRIPTIONS["dark academia"] },
    { aesthetic: "industrial", confidence: 0.65, description: AESTHETIC_DESCRIPTIONS.industrial },
    { aesthetic: "gothic", confidence: 0.42, description: "Dark romance with dramatic elements" },
  ],
  outfit_casual: [
    { aesthetic: "clean girl", confidence: 0.79, description: AESTHETIC_DESCRIPTIONS["clean girl"] },
    { aesthetic: "minimalist", confidence: 0.68, description: AESTHETIC_DESCRIPTIONS.minimalist },
    { aesthetic: "old money", confidence: 0.51, description: AESTHETIC_DESCRIPTIONS["old money"] },
  ],
  outfit_edgy: [
    { aesthetic: "indie sleaze", confidence: 0.86, description: AESTHETIC_DESCRIPTIONS["indie sleaze"] },
    { aesthetic: "grunge", confidence: 0.72, description: AESTHETIC_DESCRIPTIONS.grunge },
    { aesthetic: "streetwear", confidence: 0.58, description: AESTHETIC_DESCRIPTIONS.streetwear },
  ],
  outfit_vintage: [
    { aesthetic: "cottagecore", confidence: 0.81, description: AESTHETIC_DESCRIPTIONS.cottagecore },
    { aesthetic: "light academia", confidence: 0.74, description: AESTHETIC_DESCRIPTIONS["light academia"] },
    { aesthetic: "bohemian", confidence: 0.49, description: AESTHETIC_DESCRIPTIONS.bohemian },
  ],
};

export function getRandomVibeResults(): VibeResult[] {
  const keys = Object.keys(mockVibeResults);
  const randomKey = keys[Math.floor(Math.random() * keys.length)];
  return mockVibeResults[randomKey];
}
