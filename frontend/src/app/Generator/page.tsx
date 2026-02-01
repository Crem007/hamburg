"use client";

import { useState, useRef } from "react";
import {
  Loader2,
  Sparkles,
  Upload,
  Search,
  Play,
  ChevronDown,
  ChevronRight,
  Edit2,
  X,
  RotateCcw,
  FlipHorizontal,
  FlipVertical,
  Eraser,
  Paintbrush,
  Download,
  Undo,
  Sun,
  Contrast,
  Film,
  Image,
  Layers,
} from "lucide-react";

interface Keyframe {
  kf_id: string;
  beat_id: string;
  dialogue_or_text: string;
  action: string;
  image_prompt: string;
  shot_type: string;
  emotion_tags: string[];
}

interface KeyframeData {
  title: string;
  novel_id: string;
  keyframes: Keyframe[];
}

interface TrailerBeat {
  beat_id: string;
  role: "hook" | "conflict" | "escalation" | "cliffhanger";
  duration_sec: number;
  logline: string;
  visual_idea: string;
  key_moments: string[];
  dialogue_or_text: string[];
}

interface TrailerScript {
  style_type: "dramatic" | "action" | "mystery";
  style_display_name: string;
  style_description: string;
  novel_id: string;
  title: string;
  style_tags: string[];
  beats: TrailerBeat[];
}

const AVAILABLE_VIDEOS = [
  "KF_B1_01",
  "KF_B1_02",
  "KF_B2_01",
  "KF_B2_02",
  "KF_B2_03",
  "KF_B3_01",
  "KF_B3_02",
  "KF_B3_03",
  "KF_B4_01",
];

const SEARCH_SUGGESTIONS = ["Ghost Blows Out the Light II"];

interface DropdownSectionProps {
  title: string;
  count?: number;
  icon?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

interface LayerEditorProps {
  kfId: string;
  initialLayerIdx: number;
  onClose: () => void;
}

type EditorTool = "brush" | "eraser" | "select";

function LayerEditor({ kfId, initialLayerIdx, onClose }: LayerEditorProps) {
  const [selectedLayer, setSelectedLayer] = useState(initialLayerIdx);
  const [tool, setTool] = useState<EditorTool>("brush");
  const [brushSize, setBrushSize] = useState(10);
  const [brushColor, setBrushColor] = useState("#f97316");
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [opacity, setOpacity] = useState(100);
  const [flipH, setFlipH] = useState(false);
  const [flipV, setFlipV] = useState(false);
  const [rotation, setRotation] = useState(0);
  const [history, setHistory] = useState<string[]>([]);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);

  const layerSrc = `/demo/layers/${kfId}/layer_0${selectedLayer}.png`;

  // ... (keeping the same layer editor logic but with updated styles)

  return (
    <div className="fixed inset-0 z-50 flex bg-black/80 backdrop-blur-sm">
      {/* Left Sidebar - Layer Selection */}
      <div className="w-24 bg-white border-r border-gray-200 p-2 flex flex-col gap-2">
        <div className="text-xs text-gray-500 text-center mb-2 font-medium">
          Layers
        </div>
        {[0, 1, 2, 3].map((idx) => (
          <button
            key={idx}
            onClick={() => setSelectedLayer(idx)}
            className={`aspect-square rounded-lg overflow-hidden border-2 transition-all ${
              selectedLayer === idx
                ? "border-sky-500 shadow-md"
                : "border-transparent hover:border-gray-300"
            }`}
          >
            <img
              src={`/demo/layers/${kfId}/layer_0${idx}.png`}
              alt={`Layer ${idx}`}
              className="w-full h-full object-cover"
            />
          </button>
        ))}
      </div>

      {/* Main Canvas Area */}
      <div className="flex-1 flex flex-col bg-gray-100">
        {/* Top Toolbar */}
        <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-800">{kfId}</span>
            <span className="text-gray-300">|</span>
            <span className="text-sm text-gray-500">Layer {selectedLayer}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {}}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
              title="Undo"
            >
              <Undo size={18} />
            </button>
            <button
              onClick={() => {}}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
              title="Reset"
            >
              <RotateCcw size={18} />
            </button>
            <button
              onClick={() => {}}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
              title="Download"
            >
              <Download size={18} />
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors text-gray-600"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 flex items-center justify-center p-8 overflow-auto">
          <div className="bg-white rounded-2xl shadow-xl p-4">
            <img
              src={layerSrc}
              alt={`Layer ${selectedLayer}`}
              className="max-w-full max-h-[60vh] rounded-lg"
              style={{
                filter: `brightness(${brightness}%) contrast(${contrast}%)`,
                opacity: opacity / 100,
                transform: `${flipH ? "scaleX(-1)" : ""} ${flipV ? "scaleY(-1)" : ""} rotate(${rotation}deg)`,
              }}
            />
          </div>
        </div>
      </div>

      {/* Right Sidebar - Tools */}
      <div className="w-72 bg-white border-l border-gray-200 p-5 overflow-y-auto">
        {/* Drawing Tools */}
        <div className="mb-6">
          <div className="text-xs text-gray-500 uppercase mb-3 font-semibold tracking-wide">
            Tools
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setTool("brush")}
              className={`flex-1 p-3 rounded-xl flex items-center justify-center gap-2 transition-all font-medium ${
                tool === "brush"
                  ? "bg-gradient-to-r from-sky-400 to-blue-500 text-white shadow-md"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              <Paintbrush size={16} />
              <span className="text-sm">Brush</span>
            </button>
            <button
              onClick={() => setTool("eraser")}
              className={`flex-1 p-3 rounded-xl flex items-center justify-center gap-2 transition-all font-medium ${
                tool === "eraser"
                  ? "bg-gradient-to-r from-sky-400 to-blue-500 text-white shadow-md"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              <Eraser size={16} />
              <span className="text-sm">Eraser</span>
            </button>
          </div>
        </div>

        {/* Brush Settings */}
        <div className="mb-6">
          <div className="text-xs text-gray-500 uppercase mb-3 font-semibold tracking-wide">
            Brush Settings
          </div>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-600">Size</span>
                <span className="font-medium text-gray-800">{brushSize}px</span>
              </div>
              <input
                type="range"
                min="1"
                max="50"
                value={brushSize}
                onChange={(e) => setBrushSize(Number(e.target.value))}
                className="w-full accent-sky-500"
              />
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-2">Color</div>
              <div className="flex gap-2">
                <input
                  type="color"
                  value={brushColor}
                  onChange={(e) => setBrushColor(e.target.value)}
                  className="w-10 h-10 rounded-lg cursor-pointer border border-gray-200"
                />
                <div className="flex flex-wrap gap-1">
                  {[
                    "#f97316",
                    "#000000",
                    "#ffffff",
                    "#ef4444",
                    "#22c55e",
                    "#3b82f6",
                  ].map((color) => (
                    <button
                      key={color}
                      onClick={() => setBrushColor(color)}
                      className={`w-8 h-8 rounded-lg border-2 transition-all ${
                        brushColor === color
                          ? "border-sky-500 scale-110"
                          : "border-gray-200"
                      }`}
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Adjustments */}
        <div className="mb-6">
          <div className="text-xs text-gray-500 uppercase mb-3 font-semibold tracking-wide">
            Adjustments
          </div>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-600 flex items-center gap-1">
                  <Sun size={14} /> Brightness
                </span>
                <span className="font-medium text-gray-800">{brightness}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="200"
                value={brightness}
                onChange={(e) => setBrightness(Number(e.target.value))}
                className="w-full accent-sky-500"
              />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-600 flex items-center gap-1">
                  <Contrast size={14} /> Contrast
                </span>
                <span className="font-medium text-gray-800">{contrast}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="200"
                value={contrast}
                onChange={(e) => setContrast(Number(e.target.value))}
                className="w-full accent-sky-500"
              />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-600">Opacity</span>
                <span className="font-medium text-gray-800">{opacity}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={opacity}
                onChange={(e) => setOpacity(Number(e.target.value))}
                className="w-full accent-sky-500"
              />
            </div>
          </div>
        </div>

        {/* Transform */}
        <div className="mb-6">
          <div className="text-xs text-gray-500 uppercase mb-3 font-semibold tracking-wide">
            Transform
          </div>
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setFlipH(!flipH)}
              className={`flex-1 p-3 rounded-xl flex items-center justify-center transition-all ${
                flipH
                  ? "bg-gradient-to-r from-sky-400 to-blue-500 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              <FlipHorizontal size={18} />
            </button>
            <button
              onClick={() => setFlipV(!flipV)}
              className={`flex-1 p-3 rounded-xl flex items-center justify-center transition-all ${
                flipV
                  ? "bg-gradient-to-r from-sky-400 to-blue-500 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              <FlipVertical size={18} />
            </button>
          </div>
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">Rotation</span>
              <span className="font-medium text-gray-800">{rotation}°</span>
            </div>
            <input
              type="range"
              min="-180"
              max="180"
              value={rotation}
              onChange={(e) => setRotation(Number(e.target.value))}
              className="w-full accent-sky-500"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="space-y-2">
          <button
            onClick={onClose}
            className="w-full py-3 bg-gradient-to-r from-sky-400 to-blue-500 hover:from-sky-500 hover:to-blue-600 rounded-xl font-semibold transition-all text-white shadow-md"
          >
            Save & Close
          </button>
          <button
            onClick={onClose}
            className="w-full py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-medium transition-colors text-gray-700"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

function DropdownSection({
  title,
  count,
  icon,
  defaultOpen = false,
  children,
}: DropdownSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {icon}
          <span className="font-bold text-lg text-gray-800">{title}</span>
          {count !== undefined && (
            <span className="px-2.5 py-0.5 bg-sky-100 text-sky-700 rounded-full text-sm font-medium">
              {count}
            </span>
          )}
        </div>
        {isOpen ? (
          <ChevronDown className="text-gray-400" size={20} />
        ) : (
          <ChevronRight className="text-gray-400" size={20} />
        )}
      </button>
      {isOpen && (
        <div className="px-6 pb-6 border-t border-gray-100">{children}</div>
      )}
    </div>
  );
}

export default function GeneratorPage() {
  const [inputMode, setInputMode] = useState<"search" | "upload">("search");
  const [bookTitle, setBookTitle] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [data, setData] = useState<KeyframeData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingLayer, setEditingLayer] = useState<{
    kfId: string;
    layerIdx: number;
  } | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [trailerScripts, setTrailerScripts] = useState<TrailerScript[] | null>(null);
  const [selectedTrailerStyle, setSelectedTrailerStyle] = useState<string | null>(null);
  const [loadingScripts, setLoadingScripts] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const filteredSuggestions = SEARCH_SUGGESTIONS.filter((s) =>
    s.toLowerCase().includes(bookTitle.toLowerCase())
  );

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    setError(null);

    try {
      const text = await file.text();
      const json = JSON.parse(text) as KeyframeData;

      if (!json.keyframes || !Array.isArray(json.keyframes)) {
        throw new Error("Invalid JSON format: missing keyframes array");
      }

      setData(json);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to parse JSON file"
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadDemo = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [keyframesResponse, script1, script2, script3] = await Promise.all([
        fetch("/demo/keyframes.json"),
        fetch("/demo/trailer_script001.json").then((r) => r.json()),
        fetch("/demo/trailer_script002.json").then((r) => r.json()),
        fetch("/demo/trailer_script003.json").then((r) => r.json()),
      ]);
      if (!keyframesResponse.ok) throw new Error("Failed to load demo data");
      const json = (await keyframesResponse.json()) as KeyframeData;
      setData(json);
      setTrailerScripts([script1, script2, script3]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load demo");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!bookTitle.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const [keyframesResponse, script1, script2, script3] = await Promise.all([
        fetch("/demo/keyframes.json"),
        fetch("/demo/trailer_script001.json").then((r) => r.json()),
        fetch("/demo/trailer_script002.json").then((r) => r.json()),
        fetch("/demo/trailer_script003.json").then((r) => r.json()),
      ]);
      if (!keyframesResponse.ok) throw new Error("Book not found");
      const json = (await keyframesResponse.json()) as KeyframeData;
      setData(json);
      setTrailerScripts([script1, script2, script3]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setIsLoading(false);
    }
  };

  const hasVideo = (kfId: string) => AVAILABLE_VIDEOS.includes(kfId);

  const loadTrailerScripts = async () => {
    setLoadingScripts(true);
    try {
      const [script1, script2, script3] = await Promise.all([
        fetch("/demo/trailer_script001.json").then((r) => r.json()),
        fetch("/demo/trailer_script002.json").then((r) => r.json()),
        fetch("/demo/trailer_script003.json").then((r) => r.json()),
      ]);
      setTrailerScripts([script1, script2, script3]);
    } catch (err) {
      setError("Failed to load trailer scripts");
    } finally {
      setLoadingScripts(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            {/* Logo & Nav */}
            <div className="flex items-center gap-8">
              <a href="/market-research" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
                <h1 className="text-xl scenera-logo">Scenera</h1>
              </a>

              <nav className="hidden md:flex items-center gap-6">
                <a
                  href="/market-research"
                  className="text-gray-600 hover:text-gray-800 font-medium text-sm"
                >
                  Research
                </a>
                <a
                  href="/Generator"
                  className="text-sky-600 font-medium text-sm"
                >
                  Generator
                </a>
                <a
                  href="/editor"
                  className="text-gray-600 hover:text-gray-800 font-medium text-sm"
                >
                  Editor
                </a>
              </nav>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
        {/* Input Section - Redesigned */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          {/* Tab Header */}
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setInputMode("search")}
              className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 font-medium transition-all ${
                inputMode === "search"
                  ? "bg-sky-50 text-sky-600 border-b-2 border-sky-500"
                  : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
              }`}
            >
              <Search size={18} />
              Search by Title
            </button>
            <button
              onClick={() => setInputMode("upload")}
              className={`flex-1 flex items-center justify-center gap-2 px-6 py-4 font-medium transition-all ${
                inputMode === "upload"
                  ? "bg-sky-50 text-sky-600 border-b-2 border-sky-500"
                  : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
              }`}
            >
              <Upload size={18} />
              Upload JSON
            </button>
          </div>

          {/* Input Content */}
          <div className="p-6">
            {data && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-green-700 font-medium">{data.title}</span>
                  <span className="text-green-600 text-sm">({data.keyframes.length} keyframes loaded)</span>
                </div>
              </div>
            )}

            {inputMode === "upload" ? (
              <div className="space-y-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isLoading}
                  className="w-full py-12 border-2 border-dashed border-gray-300 rounded-xl hover:border-sky-500 hover:bg-sky-50 transition-all flex flex-col items-center justify-center gap-3 group"
                >
                  {isLoading ? (
                    <Loader2
                      className="animate-spin text-sky-500"
                      size={32}
                    />
                  ) : (
                    <>
                      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center group-hover:bg-sky-100 transition-colors">
                        <Upload className="text-gray-400 group-hover:text-sky-500 transition-colors" size={28} />
                      </div>
                      <div className="text-center">
                        <span className="text-gray-700 font-medium block">Drop your JSON file here</span>
                        <span className="text-gray-400 text-sm">or click to browse</span>
                      </div>
                    </>
                  )}
                </button>
                <div className="flex justify-center">
                  <button
                    onClick={handleLoadDemo}
                    disabled={isLoading}
                    className="px-6 py-2.5 text-sky-600 hover:text-sky-700 font-medium transition-colors"
                  >
                    Or try with demo data →
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="relative">
                  <input
                    type="text"
                    value={bookTitle}
                    onChange={(e) => {
                      setBookTitle(e.target.value);
                      setShowSuggestions(true);
                    }}
                    onFocus={() => setShowSuggestions(true)}
                    onBlur={() =>
                      setTimeout(() => setShowSuggestions(false), 150)
                    }
                    placeholder="Enter book title to search..."
                    className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-4 text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent text-lg"
                    onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  />
                  {showSuggestions && filteredSuggestions.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-xl overflow-hidden z-10 shadow-lg">
                      {filteredSuggestions.map((suggestion) => (
                        <button
                          key={suggestion}
                          onClick={() => {
                            setBookTitle(suggestion);
                            setShowSuggestions(false);
                          }}
                          className="w-full px-4 py-3 text-left hover:bg-sky-50 transition-colors text-gray-700"
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={handleSearch}
                    disabled={isLoading || !bookTitle.trim()}
                    className="flex-1 py-3 bg-gradient-to-r from-sky-400 to-blue-500 hover:from-sky-500 hover:to-blue-600 disabled:from-gray-300 disabled:to-gray-400 rounded-xl font-medium transition-all text-white shadow-md flex items-center justify-center gap-2"
                  >
                    {isLoading ? (
                      <Loader2 className="animate-spin" size={18} />
                    ) : (
                      <>
                        <Search size={18} />
                        Search
                      </>
                    )}
                  </button>
                  <button
                    onClick={handleLoadDemo}
                    disabled={isLoading}
                    className="px-6 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-medium transition-colors text-gray-700"
                  >
                    Load Demo
                  </button>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="mx-6 mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Content Sections */}
        {data && (
          <>
            {/* Trailer Script Style Selection */}
            <DropdownSection
              title="Trailer Script Style"
              icon={<Sparkles className="text-purple-500" size={22} />}
              defaultOpen={true}
            >
              {!trailerScripts ? (
                <div className="mt-4 text-center py-8">
                  <button
                    onClick={loadTrailerScripts}
                    disabled={loadingScripts}
                    className="px-6 py-3 bg-gradient-to-r from-purple-400 to-indigo-500 text-white rounded-xl font-semibold hover:from-purple-500 hover:to-indigo-600 transition-all shadow-md disabled:opacity-50"
                  >
                    {loadingScripts ? (
                      <>
                        <Loader2 className="animate-spin inline mr-2" size={18} />
                        Loading...
                      </>
                    ) : (
                      "Load Trailer Script Options"
                    )}
                  </button>
                </div>
              ) : (
                <div className="mt-4">
                  <p className="text-gray-500 text-sm mb-4 text-center">
                    Choose a trailer style that best fits your vision
                  </p>
                  <div className="grid md:grid-cols-3 gap-4">
                    {trailerScripts.map((script) => {
                      const isSelected = selectedTrailerStyle === script.style_type;
                      const styleColors: Record<string, { gradient: string; bg: string; border: string; ring: string }> = {
                        dramatic: { gradient: "from-purple-500 to-indigo-600", bg: "bg-purple-50", border: "border-purple-300", ring: "ring-purple-400" },
                        action: { gradient: "from-orange-500 to-red-600", bg: "bg-orange-50", border: "border-orange-300", ring: "ring-orange-400" },
                        mystery: { gradient: "from-teal-500 to-cyan-600", bg: "bg-teal-50", border: "border-teal-300", ring: "ring-teal-400" },
                      };
                      const colors = styleColors[script.style_type];

                      return (
                        <div
                          key={script.style_type}
                          onClick={() => setSelectedTrailerStyle(script.style_type)}
                          className={`cursor-pointer rounded-2xl border-2 transition-all overflow-hidden ${
                            isSelected
                              ? `${colors.border} ring-2 ring-offset-2 ${colors.ring}`
                              : "border-gray-200 hover:border-gray-300"
                          }`}
                        >
                          {/* Header */}
                          <div className={`bg-gradient-to-r ${colors.gradient} p-4 text-white`}>
                            <div className="font-bold">{script.style_display_name}</div>
                          </div>

                          {/* Content */}
                          <div className={`p-4 ${colors.bg}`}>
                            <p className="text-sm text-gray-600 mb-3">{script.style_description}</p>

                            {/* Stats */}
                            <div className="flex gap-3 text-xs text-gray-500 mb-3">
                              <span>{script.beats.length} beats</span>
                              <span>
                                {script.beats.reduce((sum, b) => sum + b.duration_sec, 0)}s total
                              </span>
                            </div>

                            {/* Style tags */}
                            <div className="flex flex-wrap gap-1 mb-3">
                              {script.style_tags.slice(0, 3).map((tag) => (
                                <span
                                  key={tag}
                                  className="px-2 py-0.5 bg-white rounded-full text-xs text-gray-600"
                                >
                                  {tag}
                                </span>
                              ))}
                            </div>

                            {/* Hook preview */}
                            <div className="text-sm italic text-gray-700 border-l-2 border-gray-300 pl-3">
                              &quot;{script.beats[0]?.logline}&quot;
                            </div>
                          </div>

                          {/* Selected indicator */}
                          {isSelected && (
                            <div
                              className={`bg-gradient-to-r ${colors.gradient} py-2 text-center text-white text-sm font-medium`}
                            >
                              Selected
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Continue button */}
                  {selectedTrailerStyle && (
                    <div className="mt-6 text-center">
                      <button className="px-8 py-3 bg-gradient-to-r from-sky-400 to-blue-500 text-white rounded-xl font-semibold shadow-md hover:from-sky-500 hover:to-blue-600 transition-all">
                        Continue with{" "}
                        {trailerScripts.find((s) => s.style_type === selectedTrailerStyle)?.style_display_name}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </DropdownSection>

            {/* Scene Texts */}
            <DropdownSection
              title="Scene Texts"
              count={data.keyframes.length}
              icon={<Film className="text-sky-500" size={22} />}
              defaultOpen={true}
            >
              <div className="mt-4 space-y-3">
                {data.keyframes.map((kf) => (
                  <div
                    key={kf.kf_id}
                    className="bg-gradient-to-br from-sky-50 to-blue-50 rounded-xl p-4 border border-sky-100"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-sky-600 font-mono text-sm font-semibold">
                        {kf.kf_id}
                      </span>
                      <span className="text-gray-300">|</span>
                      <span className="text-gray-500 text-sm">
                        {kf.shot_type}
                      </span>
                      <div className="flex gap-1 ml-auto">
                        {kf.emotion_tags.map((tag) => (
                          <span
                            key={tag}
                            className="px-2 py-0.5 bg-white rounded-full text-xs text-gray-600 border border-gray-200"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    <p className="text-gray-800 italic">
                      "{kf.dialogue_or_text}"
                    </p>
                    <p className="text-gray-500 text-sm mt-2">{kf.action}</p>
                  </div>
                ))}
              </div>
            </DropdownSection>

            {/* Generated Images */}
            <DropdownSection
              title="Generated Images"
              count={data.keyframes.length}
              icon={<Image className="text-blue-500" size={22} />}
            >
              <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {data.keyframes.map((kf) => (
                  <div key={kf.kf_id} className="group">
                    <div className="aspect-[9/16] bg-gray-100 rounded-xl overflow-hidden shadow-md hover:shadow-lg transition-shadow">
                      <img
                        src={`/demo/images/${kf.kf_id}.png`}
                        alt={kf.kf_id}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div className="mt-2 text-center text-xs text-gray-500 font-medium">
                      {kf.kf_id}
                    </div>
                  </div>
                ))}
              </div>
            </DropdownSection>

            {/* Extracted Layers */}
            <DropdownSection
              title="Extracted Layers"
              count={data.keyframes.length}
              icon={<Layers className="text-purple-500" size={22} />}
            >
              <div className="mt-4 space-y-4">
                {data.keyframes.map((kf) => (
                  <div
                    key={kf.kf_id}
                    className="bg-gray-50 rounded-xl p-4 border border-gray-200"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sky-600 font-mono text-sm font-semibold">
                        {kf.kf_id}
                      </span>
                      <button
                        onClick={() =>
                          setEditingLayer({ kfId: kf.kf_id, layerIdx: 0 })
                        }
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-gray-100 border border-gray-200 rounded-lg text-sm transition-colors text-gray-700"
                      >
                        <Edit2 size={14} />
                        Edit Layers
                      </button>
                    </div>
                    <div className="grid grid-cols-4 gap-2">
                      {[0, 1, 2, 3].map((layerIdx) => (
                        <div
                          key={layerIdx}
                          className="aspect-square bg-white rounded-lg overflow-hidden shadow-sm border border-gray-100"
                        >
                          <img
                            src={`/demo/layers/${kf.kf_id}/layer_0${layerIdx}.png`}
                            alt={`${kf.kf_id} Layer ${layerIdx}`}
                            className="w-full h-full object-cover"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </DropdownSection>

            {/* Generated Videos */}
            <DropdownSection
              title="Generated Videos"
              count={AVAILABLE_VIDEOS.length}
              icon={<Play className="text-green-500" size={22} />}
            >
              <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {data.keyframes.map((kf) => (
                  <div key={kf.kf_id}>
                    <div className="aspect-[9/16] bg-gray-100 rounded-xl overflow-hidden shadow-md">
                      {hasVideo(kf.kf_id) ? (
                        <video
                          src={`/demo/videos/${kf.kf_id}.mp4`}
                          controls
                          className="w-full h-full object-cover"
                          poster={`/demo/images/${kf.kf_id}.png`}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-400">
                          <div className="text-center">
                            <Play size={24} className="mx-auto mb-1 opacity-50" />
                            <span className="text-xs">Pending</span>
                          </div>
                        </div>
                      )}
                    </div>
                    <div className="mt-2 text-center text-xs text-gray-500 font-medium">
                      {kf.kf_id}
                    </div>
                  </div>
                ))}
              </div>
            </DropdownSection>

            {/* Promotional Video */}
            <div className="bg-gradient-to-r from-sky-400 via-blue-400 to-indigo-400 rounded-2xl p-8 shadow-lg">
              <h2 className="text-2xl font-bold text-white mb-1">
                Combined Promotional Trailer
              </h2>
              <p className="text-white/80 text-sm mb-6">
                All keyframes combined into a single cinematic experience
              </p>

              <div className="max-w-md mx-auto">
                <div className="aspect-[9/16] bg-black rounded-xl overflow-hidden shadow-2xl">
                  <video
                    src="/demo/trailer.mp4"
                    controls
                    className="w-full h-full object-contain"
                    poster="/demo/images/KF_B1_01.png"
                  >
                    Your browser does not support video playback.
                  </video>
                </div>
              </div>
            </div>
          </>
        )}


      </div>

      {/* Layer Edit Modal */}
      {editingLayer && (
        <LayerEditor
          kfId={editingLayer.kfId}
          initialLayerIdx={editingLayer.layerIdx}
          onClose={() => setEditingLayer(null)}
        />
      )}
    </div>
  );
}
