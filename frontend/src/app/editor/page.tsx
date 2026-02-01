"use client";

import dynamic from "next/dynamic";
import { Sparkles } from "lucide-react";

// Dynamic import to avoid SSR issues with Pixi.js
const Editor = dynamic(() => import("@/components/editor/Editor"), {
  ssr: false,
  loading: () => (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 bg-gradient-to-br from-sky-400 to-blue-500 rounded-2xl flex items-center justify-center mx-auto mb-4 animate-pulse">
          <Sparkles className="text-white" size={28} />
        </div>
        <p className="text-gray-600 font-medium">Loading Editor...</p>
      </div>
    </div>
  ),
});

export default function EditorPage() {
  return <Editor videoGenerationPath="/video_generation.json" />;
}
