/**
 * Editor state management using Zustand.
 * Extracted from viral-launch-video-main.
 */

import { create } from "zustand";
import type { Timeline } from "./types";

interface EditorState {
  timeline: Timeline | null;
  currentTime: number;
  isPlaying: boolean;
  duration: number;
  wasSeeked: boolean;

  setTimeline: (timeline: Timeline) => void;
  play: () => void;
  pause: () => void;
  seek: (time: number) => void;
  setTime: (time: number) => void;
  setTimeSmooth: (time: number) => void;
}

export const useEditorStore = create<EditorState>((set, get) => ({
  timeline: null,
  currentTime: 0,
  isPlaying: false,
  duration: 0,
  wasSeeked: false,

  setTimeline: (timeline: Timeline) => {
    // Calculate total duration based on the last item's end time
    let maxDuration = 0;
    timeline.items.forEach((item) => {
      const end = item.startTime + item.duration;
      if (end > maxDuration) {
        maxDuration = end;
      }
    });
    set({ timeline, duration: maxDuration, currentTime: 0 });
  },

  play: () => set({ isPlaying: true }),
  pause: () => set({ isPlaying: false }),

  seek: (time: number) => {
    const { duration } = get();
    const newTime = Math.max(0, Math.min(time, duration));
    set({ currentTime: newTime, wasSeeked: true });
  },

  setTime: (time: number) => {
    set({ currentTime: time, wasSeeked: true });
  },

  setTimeSmooth: (time: number) => {
    set({ currentTime: time, wasSeeked: false });
  },
}));
