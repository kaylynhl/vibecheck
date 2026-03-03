import type {
  VibeCheck,
  VibeCheckRequest,
  VibeCheckResponse,
  VibeMode,
} from "./types";
import {
  getRandomVibeResults,
  getRandomTags,
  getItemsForAesthetic,
  getPlaylistForAesthetic,
} from "../mocks";

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000";

function generateId(): string {
  return `vibe-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

async function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

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

    return {
      success: true,
      data: vibeCheck,
    };
  } catch (error) {
    console.error("Error analyzing photos:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error occurred",
    };
  }
}

export async function analyzePhotosWithBackend(
  photos: string[],
  mode: VibeMode
): Promise<VibeCheckResponse> {
  try {
    const formData = new FormData();
    formData.append("mode", mode);

    for (let i = 0; i < photos.length; i++) {
      const uri = photos[i];
      const filename = uri.split("/").pop() || `photo_${i}.jpg`;
      const match = /\.(\w+)$/.exec(filename);
      const type = match ? `image/${match[1]}` : "image/jpeg";

      formData.append("photos", {
        uri,
        name: filename,
        type,
      } as unknown as Blob);
    }

    const response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: "POST",
      body: formData,
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();

    return {
      success: true,
      data: {
        ...data,
        createdAt: new Date(data.createdAt),
      },
    };
  } catch (error) {
    console.error("Backend API error, falling back to mock:", error);
    return analyzePhotos(photos, mode);
  }
}

export async function submitFeedback(
  vibeCheckId: string,
  feedback: {
    vibeMatch?: number;
    itemsHelpful?: boolean;
    playlistMatch?: boolean;
  }
): Promise<{ success: boolean }> {
  try {
    await delay(300);
    console.log("Feedback submitted:", { vibeCheckId, feedback });
    return { success: true };
  } catch (error) {
    console.error("Error submitting feedback:", error);
    return { success: false };
  }
}

export const vibeApi = {
  analyzePhotos,
  analyzePhotosWithBackend,
  submitFeedback,
};
