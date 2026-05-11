import type {
  VibeCheck,
  VibeCheckResponse,
  VibeMode,
} from "./types";
import {
  getRandomVibeResults,
  getRandomTags,
  getItemsForAesthetic,
  getPlaylistForAesthetic,
} from "../mocks";

/**
 * Resolves the backend base URL.
 *
 *   - Phone / device: `EXPO_PUBLIC_API_URL=http://<laptop-lan-ip>:8000`
 *   - Simulator:      `EXPO_PUBLIC_API_URL=http://localhost:8000` (default)
 *   - Web:            served from same origin, `EXPO_PUBLIC_API_URL=` ok
 *
 * Set the var in `mobile/.env` -- `python scripts/serve.py` prints the LAN
 * URL on startup.
 */
const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

/** Flip to ``"1"`` (or any truthy value) to force the mock path for offline UI work. */
const USE_MOCK = process.env.EXPO_PUBLIC_USE_MOCK === "1";

function generateId(): string {
  return `vibe-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

async function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Mocked analyzer for offline / no-network demos. Kept around because the
 * UI was originally built against it -- ``analyzePhotosWithBackend`` is the
 * real entry point.
 */
export async function analyzePhotos(
  photos: string[],
  mode: VibeMode
): Promise<VibeCheckResponse> {
  try {
    await delay(1500 + Math.random() * 1000);

    const vibes = getRandomVibeResults();
    const tags = getRandomTags();
    const primaryAesthetic = vibes[0]?.aesthetic || "minimalist";
    const items = getItemsForAesthetic(primaryAesthetic);
    const playlist = getPlaylistForAesthetic(primaryAesthetic);

    const vibeCheck: VibeCheck = {
      id: generateId(),
      photos,
      mode,
      tags,
      vibes,
      itemRecommendations: items,
      playlistRecommendation: playlist,
      createdAt: new Date(),
    };

    return { success: true, data: vibeCheck };
  } catch (error) {
    console.error("Error analyzing photos:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

/** POST the picked photos to the FastAPI backend at `/api/analyze`. */
export async function analyzePhotosWithBackend(
  photos: string[],
  mode: VibeMode
): Promise<VibeCheckResponse> {
  if (USE_MOCK) {
    return analyzePhotos(photos, mode);
  }
  if (photos.length === 0) {
    return { success: false, error: "Please add at least one photo." };
  }

  try {
    const formData = new FormData();
    formData.append("mode", mode);

    for (let i = 0; i < photos.length; i++) {
      const uri = photos[i];
      const filename = uri.split("/").pop() || `photo_${i}.jpg`;
      const match = /\.(\w+)$/.exec(filename);
      const type = match ? `image/${match[1].toLowerCase()}` : "image/jpeg";

      // React Native's FormData accepts this { uri, name, type } shape and
      // streams the file from disk. Casting to `any` because the built-in
      // FormData typing only knows about Blob/string.
      formData.append("photos", {
        uri,
        name: filename,
        type,
      } as unknown as Blob);
    }

    // CRITICAL: do NOT set Content-Type manually here. React Native's fetch
    // generates the multipart boundary itself; setting Content-Type strips
    // the boundary and the server fails with 422 "Expected UploadFile".
    const response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errBody = await response.text().catch(() => "");
      throw new Error(
        `API ${response.status}${errBody ? ` -- ${errBody.slice(0, 200)}` : ""}`
      );
    }

    const data = await response.json();

    return {
      success: true,
      data: {
        ...data,
        photos,
        createdAt: data.createdAt ? new Date(data.createdAt) : new Date(),
      } as VibeCheck,
    };
  } catch (error) {
    console.error("Backend /api/analyze failed:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Network error",
    };
  }
}

/** POST a feedback row to the backend. */
export async function submitFeedback(
  vibeCheckId: string,
  feedback: {
    vibeMatch?: number;
    itemsHelpful?: boolean;
    playlistMatch?: boolean;
    notes?: string;
  }
): Promise<{ success: boolean }> {
  if (USE_MOCK) {
    await delay(200);
    console.log("[mock] feedback:", { vibeCheckId, feedback });
    return { success: true };
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ vibeCheckId, ...feedback }),
    });
    return { success: response.ok };
  } catch (error) {
    console.error("Backend /api/feedback failed:", error);
    return { success: false };
  }
}

export const vibeApi = {
  analyzePhotos,
  analyzePhotosWithBackend,
  submitFeedback,
};
