export type TagCategory =
  | "palette"
  | "lighting"
  | "texture"
  | "pattern"
  | "silhouette"
  | "material";

export interface Tag {
  id: string;
  category: TagCategory;
  value: string;
  confidence: number;
}

export interface VibeResult {
  aesthetic: string;
  confidence: number;
  description?: string;
}

export interface Track {
  id: string;
  name: string;
  artist: string;
  albumArt?: string;
  previewUrl?: string;
  durationMs?: number;
}

export interface Playlist {
  id: string;
  name: string;
  tracks: Track[];
  aesthetic: string;
  coverImage?: string;
}

export interface Item {
  id: string;
  name: string;
  imageUrl: string;
  tags: string[];
  matchScore: number;
  category: "furniture" | "decor" | "clothing" | "accessory";
  price?: string;
  source?: string;
}

export type VibeMode = "room" | "outfit";

export interface VibeCheck {
  id: string;
  photos: string[];
  mode: VibeMode;
  tags: Tag[];
  vibes: VibeResult[];
  itemRecommendations: Item[];
  playlistRecommendation: Playlist;
  createdAt: Date;
  feedback?: {
    vibeMatch?: number;
    itemsHelpful?: boolean;
    playlistMatch?: boolean;
  };
}

export interface VibeCheckRequest {
  photos: string[];
  mode: VibeMode;
}

export interface VibeCheckResponse {
  success: boolean;
  data?: VibeCheck;
  error?: string;
}
