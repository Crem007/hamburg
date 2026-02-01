import { z } from "zod";

// Scene schema and type
export const SceneSchema = z.object({
  id: z.number(),
  description: z.string(),
  prompt: z.string(),
});

export type Scene = z.infer<typeof SceneSchema>;

// Generated image schema and type
export const GeneratedImageSchema = z.object({
  id: z.number(),
  url: z.string(),
  prompt: z.string(),
});

export type GeneratedImage = z.infer<typeof GeneratedImageSchema>;

// API response schemas
export const ExtractScenesResponseSchema = z.object({
  scenes: z.array(SceneSchema),
});

export type ExtractScenesResponse = z.infer<typeof ExtractScenesResponseSchema>;

export const GenerateResponseSchema = z.object({
  images: z.array(GeneratedImageSchema),
  generation_time_seconds: z.number(),
});

export type GenerateResponse = z.infer<typeof GenerateResponseSchema>;

export const RegenerateResponseSchema = z.object({
  url: z.string(),
  generation_time_seconds: z.number(),
});

export type RegenerateResponse = z.infer<typeof RegenerateResponseSchema>;

export const BookResponseSchema = z.object({
  title: z.string(),
  author: z.string(),
  text: z.string(),
});

export type BookResponse = z.infer<typeof BookResponseSchema>;

// Style presets
export const STYLE_PRESETS = [
  { value: "cinematic", label: "Cinematic" },
  { value: "anime", label: "Anime" },
  { value: "oil_painting", label: "Oil Painting" },
  { value: "photorealistic", label: "Photorealistic" },
  { value: "watercolor", label: "Watercolor" },
  { value: "noir", label: "Noir" },
] as const;

// Character presets
export const CHARACTER_PRESETS = [
  { value: "none", label: "None" },
  { value: "Donald Trump", label: "Donald Trump" },
  { value: "Elon Musk", label: "Elon Musk" },
  { value: "custom", label: "Custom..." },
] as const;

export type InputMode = "paste" | "book" | "sample";

// Demo generation types
export interface DemoScene {
  id: number;
  description: string;
  prompt: string;
  action: string;
}

export interface DemoLayer {
  index: number;
  url: string;
}

export interface DemoGenerateUpdate {
  status: "extracting_scene" | "generating_image" | "extracting_layers" | "generating_video" | "complete" | "error";
  scene?: DemoScene;
  image_url?: string;
  layers?: DemoLayer[];
  video_url?: string;
  total_time_seconds?: number;
  error?: string;
}
