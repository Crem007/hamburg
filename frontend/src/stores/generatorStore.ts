import { create } from "zustand";
import type { Scene, GeneratedImage, InputMode } from "@/lib/types";

interface GeneratorState {
  // Input state
  inputMode: InputMode;
  text: string;
  bookTitle: string;

  // Customization
  style: string;
  character: string;
  customCharacter: string;

  // Results
  scenes: Scene[];
  images: GeneratedImage[];
  generationTime: number | null;

  // UI state
  loading: boolean;
  loadingStatus: string;
  error: string | null;

  // Actions
  setInputMode: (mode: InputMode) => void;
  setText: (text: string) => void;
  setBookTitle: (title: string) => void;
  setStyle: (style: string) => void;
  setCharacter: (character: string) => void;
  setCustomCharacter: (character: string) => void;
  setScenes: (scenes: Scene[]) => void;
  setImages: (images: GeneratedImage[]) => void;
  updateImage: (id: number, url: string) => void;
  setGenerationTime: (time: number | null) => void;
  setLoading: (loading: boolean) => void;
  setLoadingStatus: (status: string) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  inputMode: "paste" as InputMode,
  text: "",
  bookTitle: "",
  style: "cinematic",
  character: "none",
  customCharacter: "",
  scenes: [],
  images: [],
  generationTime: null,
  loading: false,
  loadingStatus: "",
  error: null,
};

export const useGeneratorStore = create<GeneratorState>((set) => ({
  ...initialState,

  setInputMode: (mode) => set({ inputMode: mode }),
  setText: (text) => set({ text }),
  setBookTitle: (title) => set({ bookTitle: title }),
  setStyle: (style) => set({ style }),
  setCharacter: (character) => set({ character }),
  setCustomCharacter: (character) => set({ customCharacter: character }),
  setScenes: (scenes) => set({ scenes }),
  setImages: (images) => set({ images }),
  updateImage: (id, url) =>
    set((state) => ({
      images: state.images.map((img) =>
        img.id === id ? { ...img, url } : img
      ),
    })),
  setGenerationTime: (time) => set({ generationTime: time }),
  setLoading: (loading) => set({ loading }),
  setLoadingStatus: (status) => set({ loadingStatus: status }),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));
