"use client";

/**
 * Main video editor component with timeline preview and export.
 * Styled to match the unified Scenera design system.
 */

import {
  Film,
  Loader2,
  Pause,
  Play,
  Volume2,
  Sparkles,
} from "lucide-react";
import * as PIXI from "pixi.js";
import { useEffect, useRef, useState } from "react";
import { PixiEditor } from "./PixiEditor";
import { useEditorStore } from "./state";
import type { Timeline } from "./types";
import { VideoExporter } from "./VideoExporter";

interface EditorProps {
  videoGenerationPath?: string;
}

export default function Editor({
  videoGenerationPath = "/video_generation.json",
}: EditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pixiAppRef = useRef<PIXI.Application | null>(null);
  const pixiEditorRef = useRef<PixiEditor | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [isRendering, setIsRendering] = useState(false);
  const [renderProgress, setRenderProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const {
    timeline,
    setTimeline,
    currentTime,
    isPlaying,
    play,
    pause,
    seek,
    duration,
  } = useEditorStore();

  // Load video generation data
  useEffect(() => {
    (async () => {
      try {
        const response = await fetch(videoGenerationPath);
        if (!response.ok) {
          throw new Error(`Failed to load ${videoGenerationPath}`);
        }
        const data = await response.json();
        console.log("Loaded video data:", data);

        let startTime = 0;
        const videos = data.generated_clips.map((clip: any) => {
          const s = startTime;
          startTime += clip.duration;
          // Handle various video URL formats
          let videoSrc = clip.video_url;
          if (videoSrc.includes("/public")) {
            videoSrc = videoSrc.split("/public")[1];
          }
          return {
            type: "video" as const,
            src: videoSrc,
            duration: clip.duration,
            startTime: s,
          };
        });
        setTimeline({ items: videos });
      } catch (e) {
        console.error("Failed to load video generation data:", e);
        setError(
          "Failed to load video data. Please ensure video_generation.json exists."
        );
      }
    })();
  }, [setTimeline, videoGenerationPath]);

  // Initialize Pixi
  useEffect(() => {
    if (!containerRef.current) return;

    const initPixi = async () => {
      if (pixiAppRef.current || !containerRef.current) return;

      const app = new PIXI.Application();
      if (!canvasRef.current) return;

      await app.init({
        width: 1280,
        height: 720,
        backgroundColor: 0x000000,
        preference: "webgl",
        resizeTo: containerRef.current,
        canvas: canvasRef.current,
      });

      pixiAppRef.current = app;

      // Initialize Editor Controller
      const currentTimeline = useEditorStore.getState().timeline || {
        items: [],
      };
      pixiEditorRef.current = new PixiEditor(app, currentTimeline as Timeline);

      // Main render loop
      app.ticker.add(() => {
        const state = useEditorStore.getState();

        if (state.isPlaying) {
          let newTime = state.currentTime + app.ticker.deltaMS / 1000;

          if (pixiEditorRef.current) {
            const videoTime = pixiEditorRef.current.getCurrentTime();
            if (videoTime !== null) {
              newTime = videoTime;
            }
          }

          if (newTime >= state.duration) {
            state.pause();
            state.setTime(state.duration);
          } else {
            state.setTimeSmooth(newTime);
          }
        }

        if (pixiEditorRef.current) {
          pixiEditorRef.current.update(
            state.currentTime,
            state.isPlaying,
            state.wasSeeked
          );
        }
      });
    };

    initPixi();

    return () => {
      if (pixiEditorRef.current) {
        pixiEditorRef.current.destroy();
        pixiEditorRef.current = null;
      }

      const app = pixiAppRef.current;
      if (app) {
        app.destroy(true, { children: true, texture: true });
        pixiAppRef.current = null;
      }
    };
  }, []);

  // Handle timeline updates
  useEffect(() => {
    if (pixiEditorRef.current && timeline) {
      pixiEditorRef.current.updateTimeline(timeline);
    }
  }, [timeline]);

  const handleRender = async () => {
    if (!pixiEditorRef.current) return;
    setIsRendering(true);
    setRenderProgress(0);

    try {
      const mp4Buffer = await VideoExporter.export(pixiEditorRef.current, {
        fps: 30,
        duration: duration,
        onProgress: (p) => {
          setRenderProgress(p);
          console.log(`Rendering: ${(p * 100).toFixed(0)}%`);
        },
      });

      const videoBlob = new Blob([mp4Buffer as unknown as BlobPart], {
        type: "video/mp4",
      });
      const videoUrl = URL.createObjectURL(videoBlob);

      // Download the video
      const a = document.createElement("a");
      a.href = videoUrl;
      a.download = `novel_trailer_${Date.now()}.mp4`;
      a.click();
      a.remove();

      setIsRendering(false);
    } catch (error) {
      console.error("Render failed", error);
      setIsRendering(false);
      setError("Rendering failed. Please try again.");
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 100);
    return `${mins.toString().padStart(2, "0")}:${secs
      .toString()
      .padStart(2, "0")}.${ms.toString().padStart(2, "0")}`;
  };

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl border border-gray-200 p-8 max-w-md text-center shadow-lg">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Film className="text-red-500" size={28} />
          </div>
          <h2 className="text-xl font-bold text-gray-800 mb-2">
            Failed to Load
          </h2>
          <p className="text-gray-500 text-sm mb-4">{error}</p>
          <p className="text-gray-400 text-xs">
            Make sure to run the video generation pipeline first.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            {/* Logo & Nav */}
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-2">
                <h1 className="text-xl scenera-logo">Scenera</h1>
              </div>

              <nav className="hidden md:flex items-center gap-6">
                <a
                  href="/market-research"
                  className="text-gray-600 hover:text-gray-800 font-medium text-sm"
                >
                  Research
                </a>
                <a
                  href="/Generator"
                  className="text-gray-600 hover:text-gray-800 font-medium text-sm"
                >
                  Generator
                </a>
                <a
                  href="/editor"
                  className="text-sky-600 font-medium text-sm"
                >
                  Editor
                </a>
              </nav>
            </div>

            {/* Export Button */}
            <button
              onClick={handleRender}
              disabled={isRendering || !timeline}
              className="px-5 py-2.5 bg-gradient-to-r from-sky-400 to-blue-500 hover:from-sky-500 hover:to-blue-600 disabled:from-gray-300 disabled:to-gray-400 text-white rounded-xl font-medium transition-all flex items-center gap-2 shadow-md"
            >
              {isRendering ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Rendering... {(renderProgress * 100).toFixed(0)}%
                </>
              ) : (
                <>
                  <Film size={18} />
                  Export Video
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
        {/* Main Player */}
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
          <div className="aspect-video bg-black relative">
            <div ref={containerRef} className="w-full h-full">
              <canvas ref={canvasRef} className="w-full h-full" />
            </div>

            {/* Play button overlay */}
            {!isPlaying && (
              <div className="absolute inset-0 flex items-center justify-center">
                <button
                  onClick={() => play()}
                  className="w-20 h-20 rounded-full bg-gradient-to-r from-sky-400 to-blue-500 flex items-center justify-center hover:scale-105 transition-transform shadow-xl"
                >
                  <Play fill="white" className="text-white ml-1" size={32} />
                </button>
              </div>
            )}

            {/* Controls overlay */}
            <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/90 to-transparent">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => (isPlaying ? pause() : play())}
                  className="text-white hover:text-sky-400 transition-colors"
                >
                  {isPlaying ? (
                    <Pause size={22} fill="currentColor" />
                  ) : (
                    <Play size={22} fill="currentColor" />
                  )}
                </button>

                {/* Seek Bar */}
                <button
                  className="flex-1 h-2 bg-white/20 rounded-full overflow-hidden relative cursor-pointer group"
                  onClick={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const pct = x / rect.width;
                    seek(pct * duration);
                  }}
                >
                  <div
                    className="h-full bg-gradient-to-r from-sky-400 to-blue-500 absolute top-0 left-0 transition-all"
                    style={{ width: `${(currentTime / duration) * 100}%` }}
                  />
                </button>

                <span className="text-sm font-mono text-white/80 w-28 text-right">
                  {formatTime(currentTime)} / {formatTime(duration)}
                </span>

                <Volume2 size={20} className="text-white/60" />
              </div>
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center gap-3 mb-3">
            <Film className="text-sky-500" size={20} />
            <h3 className="font-semibold text-gray-800">Timeline</h3>
            <span className="px-2 py-0.5 bg-sky-100 text-sky-700 rounded-full text-xs font-medium">
              {timeline?.items.length || 0} clips
            </span>
          </div>

          <div className="h-20 bg-gray-50 rounded-xl border border-gray-200 p-2 relative overflow-hidden">
            {/* Timeline Cursor */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-sky-500 z-20 shadow-lg"
              style={{ left: `${(currentTime / duration) * 100}%` }}
            >
              <div className="w-3 h-3 bg-sky-500 rounded-full -ml-1 -mt-1" />
            </div>

            {/* Track Items */}
            <div className="relative w-full h-full">
              {timeline?.items.map((item, idx) => {
                const startPct = (item.startTime / duration) * 100;
                const widthPct = (item.duration / duration) * 100;

                return (
                  <div
                    key={`${item.type}-${item.startTime}-${idx}`}
                    className={`absolute h-12 rounded-lg border overflow-hidden text-xs p-2 transition-all hover:shadow-md ${
                      item.type === "video"
                        ? "bg-gradient-to-r from-blue-100 to-blue-50 border-blue-200 top-1"
                        : "bg-gradient-to-r from-purple-100 to-purple-50 border-purple-200 top-1"
                    }`}
                    style={{
                      left: `${startPct}%`,
                      width: `${widthPct}%`,
                    }}
                  >
                    <div className="font-medium text-gray-700 truncate">
                      {item.type === "video"
                        ? item.src.split("/").pop()
                        : "Overlay"}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Click to seek */}
            <button
              className="absolute inset-0 z-10 w-full h-full cursor-pointer bg-transparent"
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const pct = x / rect.width;
                seek(pct * duration);
              }}
            />
          </div>
        </div>

        {/* Rendering Progress */}
        {isRendering && (
          <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-sky-100 rounded-full flex items-center justify-center">
                <Loader2 className="text-sky-500 animate-spin" size={24} />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-800 mb-1">
                  Exporting Video...
                </h3>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-sky-400 to-blue-500 transition-all"
                    style={{ width: `${renderProgress * 100}%` }}
                  />
                </div>
              </div>
              <span className="text-lg font-bold text-sky-600">
                {(renderProgress * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
