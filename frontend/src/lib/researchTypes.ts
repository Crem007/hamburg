import { z } from "zod";

// Request schema
export const ResearchRequestSchema = z.object({
  topic: z.string().default("web_novel_trends"),
  genres: z.array(z.string()).default([]),
  platforms: z.array(z.string()).default([]),
});

export type ResearchRequest = z.infer<typeof ResearchRequestSchema>;

// Task schema
export const ResearchTaskSchema = z.object({
  task_id: z.string(),
  status: z.enum(["pending", "running", "completed", "failed"]),
  created_at: z.string(),
  progress: z.number().nullable().optional(),
});

export type ResearchTask = z.infer<typeof ResearchTaskSchema>;

// Genre insight schema
export const GenreInsightSchema = z.object({
  name: z.string(),
  popularity_score: z.number(),
  growth_trend: z.enum(["rising", "stable", "declining"]),
  key_themes: z.array(z.string()),
  visual_style: z.string(),
  description: z.string().default(""),
});

export type GenreInsight = z.infer<typeof GenreInsightSchema>;

// Novel recommendation schema
export const NovelRecommendationSchema = z.object({
  title: z.string(),
  author: z.string(),
  genre: z.string(),
  platform: z.string(),
  rating: z.number(),
  synopsis: z.string(),
  trailer_potential: z.enum(["high", "medium", "low"]),
  visual_hooks: z.array(z.string()),
});

export type NovelRecommendation = z.infer<typeof NovelRecommendationSchema>;

// Trailer idea schema
export const TrailerIdeaSchema = z.object({
  title: z.string(),
  description: z.string(),
  visual_elements: z.array(z.string()),
  target_emotion: z.string(),
  suggested_music_style: z.string(),
});

export type TrailerIdea = z.infer<typeof TrailerIdeaSchema>;

// Full report schema
export const ResearchReportSchema = z.object({
  id: z.string(),
  title: z.string(),
  summary: z.string(),
  created_at: z.string(),
  genres: z.array(GenreInsightSchema),
  trending_novels: z.array(NovelRecommendationSchema),
  trailer_suggestions: z.array(TrailerIdeaSchema),
  platforms_analyzed: z.array(z.string()),
});

export type ResearchReport = z.infer<typeof ResearchReportSchema>;

// Report list schema
export const ResearchReportListSchema = z.object({
  reports: z.array(ResearchReportSchema),
});

export type ResearchReportList = z.infer<typeof ResearchReportListSchema>;

// Available platforms
export const RESEARCH_PLATFORMS = [
  { value: "webnovel", label: "Webnovel (Qidian)" },
  { value: "royal_road", label: "Royal Road" },
  { value: "wattpad", label: "Wattpad" },
  { value: "tapas", label: "Tapas" },
  { value: "kindle", label: "Kindle Unlimited" },
  { value: "scribble_hub", label: "Scribble Hub" },
] as const;

// Popular genres
export const RESEARCH_GENRES = [
  { value: "fantasy", label: "Fantasy" },
  { value: "romance", label: "Romance" },
  { value: "sci_fi", label: "Sci-Fi" },
  { value: "action", label: "Action" },
  { value: "horror", label: "Horror" },
  { value: "mystery", label: "Mystery" },
  { value: "slice_of_life", label: "Slice of Life" },
  { value: "isekai", label: "Isekai" },
  { value: "litrpg", label: "LitRPG" },
  { value: "cultivation", label: "Cultivation" },
] as const;
