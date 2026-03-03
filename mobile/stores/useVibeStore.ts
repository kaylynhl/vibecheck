import { create } from "zustand";
import type { VibeCheck, VibeMode } from "../services/types";

interface VibeState {
  selectedPhotos: string[];
  mode: VibeMode;
  isAnalyzing: boolean;
  currentVibeCheck: VibeCheck | null;
  vibeHistory: VibeCheck[];

  addPhoto: (uri: string) => void;
  removePhoto: (uri: string) => void;
  clearPhotos: () => void;
  setMode: (mode: VibeMode) => void;
  setIsAnalyzing: (isAnalyzing: boolean) => void;
  setCurrentVibeCheck: (vibeCheck: VibeCheck | null) => void;
  addToHistory: (vibeCheck: VibeCheck) => void;
  clearHistory: () => void;
  getVibeById: (id: string) => VibeCheck | undefined;
}

export const useVibeStore = create<VibeState>((set, get) => ({
  selectedPhotos: [],
  mode: "room",
  isAnalyzing: false,
  currentVibeCheck: null,
  vibeHistory: [],

  addPhoto: (uri: string) =>
    set((state) => ({
      selectedPhotos: [...state.selectedPhotos, uri],
    })),

  removePhoto: (uri: string) =>
    set((state) => ({
      selectedPhotos: state.selectedPhotos.filter((photo) => photo !== uri),
    })),

  clearPhotos: () => set({ selectedPhotos: [] }),

  setMode: (mode: VibeMode) => set({ mode }),

  setIsAnalyzing: (isAnalyzing: boolean) => set({ isAnalyzing }),

  setCurrentVibeCheck: (vibeCheck: VibeCheck | null) =>
    set({ currentVibeCheck: vibeCheck }),

  addToHistory: (vibeCheck: VibeCheck) =>
    set((state) => ({
      vibeHistory: [vibeCheck, ...state.vibeHistory],
    })),

  clearHistory: () => set({ vibeHistory: [] }),

  getVibeById: (id: string) => {
    const state = get();
    return state.vibeHistory.find((vibe) => vibe.id === id);
  },
}));
