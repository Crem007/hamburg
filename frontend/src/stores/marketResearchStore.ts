import { create } from "zustand";
import type {
  ResearchTask,
  ResearchReport,
  GenreInsight,
  NovelRecommendation,
  TrailerIdea,
} from "@/lib/researchTypes";

interface MarketResearchState {
  // Current research task
  currentTask: ResearchTask | null;
  isPolling: boolean;

  // Research results
  reports: ResearchReport[];
  selectedReport: ResearchReport | null;

  // Filter state
  selectedGenres: string[];
  selectedPlatforms: string[];

  // UI state
  loading: boolean;
  loadingStatus: string;
  error: string | null;

  // View state
  expandedSections: {
    genres: boolean;
    platforms: boolean;
    novels: boolean;
    trailers: boolean;
  };

  // Actions
  setCurrentTask: (task: ResearchTask | null) => void;
  setIsPolling: (polling: boolean) => void;
  setReports: (reports: ResearchReport[]) => void;
  addReport: (report: ResearchReport) => void;
  setSelectedReport: (report: ResearchReport | null) => void;
  setSelectedGenres: (genres: string[]) => void;
  setSelectedPlatforms: (platforms: string[]) => void;
  toggleGenre: (genre: string) => void;
  togglePlatform: (platform: string) => void;
  setLoading: (loading: boolean) => void;
  setLoadingStatus: (status: string) => void;
  setError: (error: string | null) => void;
  toggleSection: (section: keyof MarketResearchState["expandedSections"]) => void;
  reset: () => void;
}

const initialState = {
  currentTask: null,
  isPolling: false,
  reports: [],
  selectedReport: null,
  selectedGenres: [],
  selectedPlatforms: [],
  loading: false,
  loadingStatus: "",
  error: null,
  expandedSections: {
    genres: true,
    platforms: true,
    novels: true,
    trailers: true,
  },
};

export const useMarketResearchStore = create<MarketResearchState>((set) => ({
  ...initialState,

  setCurrentTask: (task) => set({ currentTask: task }),
  setIsPolling: (polling) => set({ isPolling: polling }),
  setReports: (reports) => set({ reports }),
  addReport: (report) =>
    set((state) => ({
      reports: [report, ...state.reports.filter((r) => r.id !== report.id)],
    })),
  setSelectedReport: (report) => set({ selectedReport: report }),
  setSelectedGenres: (genres) => set({ selectedGenres: genres }),
  setSelectedPlatforms: (platforms) => set({ selectedPlatforms: platforms }),
  toggleGenre: (genre) =>
    set((state) => ({
      selectedGenres: state.selectedGenres.includes(genre)
        ? state.selectedGenres.filter((g) => g !== genre)
        : [...state.selectedGenres, genre],
    })),
  togglePlatform: (platform) =>
    set((state) => ({
      selectedPlatforms: state.selectedPlatforms.includes(platform)
        ? state.selectedPlatforms.filter((p) => p !== platform)
        : [...state.selectedPlatforms, platform],
    })),
  setLoading: (loading) => set({ loading }),
  setLoadingStatus: (status) => set({ loadingStatus: status }),
  setError: (error) => set({ error }),
  toggleSection: (section) =>
    set((state) => ({
      expandedSections: {
        ...state.expandedSections,
        [section]: !state.expandedSections[section],
      },
    })),
  reset: () => set(initialState),
}));

// Selectors for computed values
export const selectFilteredNovels = (state: MarketResearchState): NovelRecommendation[] => {
  const report = state.selectedReport;
  if (!report) return [];

  let novels = report.trending_novels;

  if (state.selectedGenres.length > 0) {
    novels = novels.filter((n) =>
      state.selectedGenres.some((g) =>
        n.genre.toLowerCase().includes(g.toLowerCase())
      )
    );
  }

  if (state.selectedPlatforms.length > 0) {
    novels = novels.filter((n) =>
      state.selectedPlatforms.some((p) =>
        n.platform.toLowerCase().includes(p.toLowerCase())
      )
    );
  }

  return novels;
};

export const selectGenreStats = (state: MarketResearchState): GenreInsight[] => {
  const report = state.selectedReport;
  if (!report) return [];
  return report.genres;
};

export const selectTrailerIdeas = (state: MarketResearchState): TrailerIdea[] => {
  const report = state.selectedReport;
  if (!report) return [];
  return report.trailer_suggestions;
};
