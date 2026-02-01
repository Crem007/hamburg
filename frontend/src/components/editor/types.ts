/**
 * Timeline types for the video editor.
 * Extracted from viral-launch-video-main.
 */

import { z } from "zod";

export const TimelineItemVideoSchema = z.object({
  type: z.literal("video"),
  src: z.string(),
  duration: z.number(),
  startTime: z.number(),
});

export type TimelineItemVideo = z.infer<typeof TimelineItemVideoSchema>;

export const OverlayElementTextSchema = z.object({
  type: z.literal("text"),
  text: z.string(),
  position: z.enum(["top", "bottom", "center"]),
  size: z.enum(["small", "medium", "large"]),
  color: z.string().optional().default("#ffffff"),
  backgroundColor: z
    .union([z.string(), z.literal("transparent")])
    .optional()
    .default("transparent"),
});

export type OverlayElementText = z.infer<typeof OverlayElementTextSchema>;

export const OverlayElementImageSchema = z.object({
  type: z.literal("image"),
  src: z.string(),
  position: z.enum(["top", "bottom", "center"]),
  size: z.enum(["small", "medium", "large"]),
});

export type OverlayElementImage = z.infer<typeof OverlayElementImageSchema>;

export const OverlayElementSchema = z.discriminatedUnion("type", [
  OverlayElementTextSchema,
  OverlayElementImageSchema,
]);

export type OverlayElement = z.infer<typeof OverlayElementSchema>;

export const TimelineItemOverlaySchema = z.object({
  type: z.literal("overlay"),
  duration: z.number(),
  startTime: z.number(),
  layout: z.array(OverlayElementSchema),
});

export type TimelineItemOverlay = z.infer<typeof TimelineItemOverlaySchema>;

const TimelineItemSchema = z.discriminatedUnion("type", [
  TimelineItemVideoSchema,
  TimelineItemOverlaySchema,
]);

export type TimelineItem = z.infer<typeof TimelineItemSchema>;

const TimelineSchema = z.object({
  items: z.array(TimelineItemSchema),
});

export type Timeline = z.infer<typeof TimelineSchema>;
