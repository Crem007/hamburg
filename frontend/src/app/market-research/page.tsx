"use client";

import { useState, useEffect } from "react";
import {
  Loader2,
  ChevronDown,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Minus,
  Star,
  Sparkles,
  BookOpen,
  Film,
  Clock,
  Filter,
  X,
  Flame,
  Megaphone,
  Play,
} from "lucide-react";
import {
  startResearch,
  listResearchReports,
  getResearchReport,
  pollResearchTask,
  getResearchMarkdown,
} from "@/lib/researchApi";
import type {
  ResearchReport,
  GenreInsight,
  NovelRecommendation,
  TrailerIdea,
} from "@/lib/researchTypes";
import { RESEARCH_GENRES, RESEARCH_PLATFORMS } from "@/lib/researchTypes";

// ============================================================================
// Dropdown Section Component
// ============================================================================

interface DropdownSectionProps {
  title: string;
  count?: number;
  icon?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
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

// ============================================================================
// Genre Card Component
// ============================================================================

interface GenreCardProps {
  genre: GenreInsight;
}

function GenreCard({ genre }: GenreCardProps) {
  const trendIcon =
    genre.growth_trend === "rising" ? (
      <TrendingUp className="text-green-500" size={16} />
    ) : genre.growth_trend === "declining" ? (
      <TrendingDown className="text-red-500" size={16} />
    ) : (
      <Minus className="text-gray-400" size={16} />
    );

  const trendColor =
    genre.growth_trend === "rising"
      ? "text-green-600"
      : genre.growth_trend === "declining"
      ? "text-red-600"
      : "text-gray-500";

  return (
    <div className="bg-gradient-to-br from-sky-50 to-blue-50 rounded-xl p-4 hover:shadow-md transition-all border border-sky-100">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-gray-800">{genre.name}</h3>
        <div className="flex items-center gap-1">
          {trendIcon}
          <span className={`text-sm font-medium ${trendColor}`}>
            {Math.round(genre.popularity_score)}%
          </span>
        </div>
      </div>
      <div className="text-sm text-gray-500 mb-2">{genre.visual_style}</div>
      {genre.key_themes.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {genre.key_themes.slice(0, 3).map((theme, idx) => (
            <span
              key={idx}
              className="px-2 py-0.5 bg-white rounded-full text-xs text-gray-600 border border-gray-200"
            >
              {theme}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Novel Card Component
// ============================================================================

interface NovelCardProps {
  novel: NovelRecommendation;
}

function NovelCard({ novel }: NovelCardProps) {
  const [expanded, setExpanded] = useState(false);

  const potentialStyles = {
    high: "text-green-700 bg-green-100 border-green-200",
    medium: "text-sky-700 bg-sky-100 border-sky-200",
    low: "text-gray-600 bg-gray-100 border-gray-200",
  };

  return (
    <div className="bg-white rounded-xl p-5 border border-gray-200 hover:shadow-lg transition-all">
      <div className="flex gap-4">
        {/* Book Cover Placeholder */}
        <div className="w-20 h-28 bg-gradient-to-br from-sky-200 to-blue-300 rounded-lg flex-shrink-0 flex items-center justify-center shadow-md">
          <BookOpen className="text-white/80" size={24} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-1">
            <h3 className="font-bold text-gray-800 flex items-center gap-2">
              {novel.trailer_potential === "high" && (
                <span className="text-blue-500">🔥</span>
              )}
              {novel.title}
            </h3>
            <div className="flex items-center gap-1 text-sky-500 flex-shrink-0">
              <Star size={14} fill="currentColor" />
              <span className="text-sm font-medium">{novel.rating.toFixed(1)}</span>
            </div>
          </div>

          <div className="text-sm text-gray-500 mb-2">by {novel.author}</div>

          <div className="flex flex-wrap gap-1.5 mb-3">
            <span className="px-2.5 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium border border-blue-200">
              {novel.genre}
            </span>
            <span className="px-2.5 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs font-medium border border-purple-200">
              {novel.platform}
            </span>
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                potentialStyles[novel.trailer_potential as keyof typeof potentialStyles]
              }`}
            >
              {novel.trailer_potential.toUpperCase()}
            </span>
          </div>

          {novel.synopsis && (
            <p className="text-sm text-gray-600 mb-3 line-clamp-2">
              {novel.synopsis}
            </p>
          )}

          {novel.visual_hooks.length > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-sm text-sky-600 hover:text-sky-700 font-medium flex items-center gap-1"
            >
              <Play size={12} />
              {expanded ? "Hide" : "View"} Trailer Hooks
            </button>
          )}
        </div>
      </div>

      {expanded && novel.visual_hooks.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-2 font-medium">
            Visual Hooks for Trailer
          </div>
          <ul className="space-y-1.5">
            {novel.visual_hooks.map((hook, idx) => (
              <li
                key={idx}
                className="text-sm text-gray-700 flex items-start gap-2"
              >
                <span className="text-sky-500 mt-0.5">●</span>
                {hook}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Trailer Idea Card Component
// ============================================================================

interface TrailerIdeaCardProps {
  idea: TrailerIdea;
}

function TrailerIdeaCard({ idea }: TrailerIdeaCardProps) {
  return (
    <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-5 border border-purple-100 hover:shadow-md transition-all">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
          <Film className="text-white" size={16} />
        </div>
        <h3 className="font-bold text-gray-800">{idea.title}</h3>
      </div>

      {idea.description && (
        <p className="text-sm text-gray-600 mb-3">{idea.description}</p>
      )}

      <div className="flex flex-wrap gap-1.5 mb-3">
        <span className="px-2.5 py-0.5 bg-pink-100 text-pink-700 rounded-full text-xs font-medium border border-pink-200">
          {idea.target_emotion}
        </span>
        <span className="px-2.5 py-0.5 bg-indigo-100 text-indigo-700 rounded-full text-xs font-medium border border-indigo-200">
          {idea.suggested_music_style}
        </span>
      </div>

      {idea.visual_elements.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1.5 font-medium">
            Visual Elements
          </div>
          <div className="flex flex-wrap gap-1">
            {idea.visual_elements.map((element, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 bg-white rounded-full text-xs text-gray-600 border border-gray-200"
              >
                {element}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Markdown Renderer Component
// ============================================================================

function MarkdownRenderer({ content }: { content: string }) {
  // Parse markdown and render with proper styling
  const parseMarkdown = (md: string) => {
    const lines = md.split('\n');
    const elements: React.ReactNode[] = [];
    let i = 0;
    let tableRows: string[][] = [];
    let inTable = false;
    let tableHeaders: string[] = [];
    let listItems: string[] = [];
    let inList = false;
    let nestedListItems: string[] = [];
    let inNestedList = false;

    const flushTable = (key: string) => {
      if (tableHeaders.length > 0 || tableRows.length > 0) {
        elements.push(
          <div key={key} className="my-6 overflow-x-auto rounded-xl border border-gray-200 shadow-sm">
            <table className="min-w-full">
              {tableHeaders.length > 0 && (
                <thead className="bg-gradient-to-r from-sky-50 via-blue-50 to-indigo-50">
                  <tr>
                    {tableHeaders.map((header, idx) => (
                      <th key={idx} className="px-5 py-4 text-left text-sm font-semibold text-gray-700 border-b border-gray-200 first:rounded-tl-xl last:rounded-tr-xl">
                        {formatInlineStylesJSX(header, `th-${idx}`)}
                      </th>
                    ))}
                  </tr>
                </thead>
              )}
              <tbody className="bg-white divide-y divide-gray-100">
                {tableRows.map((row, rowIdx) => (
                  <tr key={rowIdx} className="hover:bg-gray-50 transition-colors">
                    {row.map((cell, cellIdx) => (
                      <td key={cellIdx} className="px-5 py-4 text-sm text-gray-600">
                        {formatInlineStylesJSX(cell, `cell-${rowIdx}-${cellIdx}`)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        tableRows = [];
        tableHeaders = [];
        inTable = false;
      }
    };

    const flushList = (key: string) => {
      if (listItems.length > 0) {
        elements.push(
          <ul key={key} className="my-4 space-y-3 pl-1">
            {listItems.map((item, idx) => (
              <li key={idx} className="flex items-start gap-3 text-gray-600">
                <span className="w-2 h-2 bg-gradient-to-br from-sky-400 to-blue-500 rounded-full mt-2 flex-shrink-0 shadow-sm"></span>
                <span className="leading-relaxed">{formatInlineStylesJSX(item, `li-${idx}`)}</span>
              </li>
            ))}
          </ul>
        );
        listItems = [];
        inList = false;
      }
    };

    const flushNestedList = (key: string) => {
      if (nestedListItems.length > 0) {
        elements.push(
          <ul key={key} className="my-2 ml-6 space-y-2 border-l-2 border-sky-200 pl-4">
            {nestedListItems.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2 text-gray-500 text-sm">
                <span className="w-1.5 h-1.5 bg-sky-300 rounded-full mt-2 flex-shrink-0"></span>
                <span className="leading-relaxed">{formatInlineStylesJSX(item, `nested-li-${idx}`)}</span>
              </li>
            ))}
          </ul>
        );
        nestedListItems = [];
        inNestedList = false;
      }
    };

    while (i < lines.length) {
      const line = lines[i];

      // Skip empty lines but flush pending content
      if (line.trim() === '') {
        flushNestedList(`nested-${i}`);
        flushList(`list-${i}`);
        flushTable(`table-${i}`);
        i++;
        continue;
      }

      // H1 - Document Title
      if (line.startsWith('# ')) {
        flushTable(`table-h1-${i}`);
        flushList(`list-h1-${i}`);
        elements.push(
          <div key={i} className="mb-8 mt-4">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">
              {formatInlineStylesJSX(line.slice(2), 'h1')}
            </h1>
            <div className="h-1 w-24 bg-gradient-to-r from-sky-400 to-blue-500 rounded-full"></div>
          </div>
        );
        i++;
        continue;
      }

      // H2 - Major Section
      if (line.startsWith('## ')) {
        flushTable(`table-h2-${i}`);
        flushList(`list-h2-${i}`);
        elements.push(
          <div key={i} className="mt-10 mb-6">
            <div className="flex items-center gap-3">
              <div className="w-1.5 h-8 bg-gradient-to-b from-sky-400 to-blue-500 rounded-full"></div>
              <h2 className="text-2xl font-bold text-gray-800">
                {formatInlineStylesJSX(line.slice(3), 'h2')}
              </h2>
            </div>
          </div>
        );
        i++;
        continue;
      }

      // H3 - Sub Section with card styling
      if (line.startsWith('### ')) {
        flushTable(`table-h3-${i}`);
        flushList(`list-h3-${i}`);
        
        // Check if this is followed by a table (genre card pattern)
        let hasTable = false;
        let j = i + 1;
        while (j < lines.length && lines[j].trim() === '') j++;
        if (j < lines.length && lines[j].startsWith('|')) {
          hasTable = true;
        }
        
        if (hasTable) {
          // Start a card container for H3 + Table
          elements.push(
            <div key={i} className="mt-8 mb-2">
              <div className="bg-gradient-to-r from-sky-50 to-blue-50 rounded-t-xl px-5 py-3 border border-b-0 border-gray-200">
                <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                  <span className="w-2 h-2 bg-sky-500 rounded-full"></span>
                  {formatInlineStylesJSX(line.slice(4), 'h3')}
                </h3>
              </div>
            </div>
          );
        } else {
          elements.push(
            <h3 key={i} className="text-xl font-semibold text-gray-700 mt-8 mb-3 flex items-center gap-2">
              <span className="w-2 h-2 bg-gradient-to-br from-sky-400 to-blue-500 rounded-full"></span>
              {formatInlineStylesJSX(line.slice(4), 'h3')}
            </h3>
          );
        }
        i++;
        continue;
      }

      // Table detection
      if (line.startsWith('|')) {
        const cells = line.split('|').filter(c => c.trim()).map(c => c.trim());
        
        if (!inTable) {
          tableHeaders = cells;
          inTable = true;
          i++;
          // Skip separator row
          if (i < lines.length && lines[i].includes('---')) {
            i++;
          }
          continue;
        } else {
          tableRows.push(cells);
          i++;
          continue;
        }
      }

      // Nested bullet points (indented with spaces/tabs + -)
      if (line.match(/^[\s]{2,}- /)) {
        flushList(`list-before-nested-${i}`);
        const item = line.replace(/^[\s]+- /, '');
        nestedListItems.push(item);
        inNestedList = true;
        i++;
        continue;
      }

      // Top-level bullet points
      if (line.startsWith('- ')) {
        flushNestedList(`nested-before-list-${i}`);
        listItems.push(line.slice(2));
        inList = true;
        i++;
        continue;
      }

      // Regular paragraph
      if (line.trim()) {
        flushTable(`table-p-${i}`);
        flushList(`list-p-${i}`);
        flushNestedList(`nested-p-${i}`);
        elements.push(
          <p key={i} className="text-gray-600 leading-relaxed my-4 text-base">
            {formatInlineStylesJSX(line, `p-${i}`)}
          </p>
        );
      }
      i++;
    }

    // Flush any remaining content
    flushNestedList('final-nested');
    flushList('final-list');
    flushTable('final-table');

    return elements;
  };

  // Format inline styles and return JSX instead of HTML string
  const formatInlineStylesJSX = (text: string, keyPrefix: string): React.ReactNode => {
    const parts: React.ReactNode[] = [];
    let remaining = text;
    let partIndex = 0;

    // Process bold, italic, and code
    const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      // Add text before match
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index));
      }

      if (match[2]) {
        // Bold **text**
        parts.push(
          <strong key={`${keyPrefix}-bold-${partIndex++}`} className="text-gray-800 font-semibold">
            {match[2]}
          </strong>
        );
      } else if (match[3]) {
        // Italic *text*
        parts.push(
          <em key={`${keyPrefix}-italic-${partIndex++}`} className="italic text-gray-600">
            {match[3]}
          </em>
        );
      } else if (match[4]) {
        // Code `text`
        parts.push(
          <code key={`${keyPrefix}-code-${partIndex++}`} className="bg-sky-50 text-sky-700 px-2 py-0.5 rounded-md text-sm font-mono border border-sky-100">
            {match[4]}
          </code>
        );
      }

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  const formatInlineStyles = (text: string): string => {
    // Bold
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-800 font-semibold">$1</strong>');
    // Italic
    text = text.replace(/\*(.+?)\*/g, '<em class="italic">$1</em>');
    // Code
    text = text.replace(/`(.+?)`/g, '<code class="bg-sky-50 text-sky-700 px-2 py-0.5 rounded-md text-sm font-mono border border-sky-100">$1</code>');
    return text;
  };

  return (
    <article className="prose prose-gray max-w-none">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 md:p-10">
        {parseMarkdown(content)}
      </div>
    </article>
  );
}

// ============================================================================
// Main Page Component
// ============================================================================

export default function MarketResearchPage() {
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [reports, setReports] = useState<ResearchReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<ResearchReport | null>(
    null
  );

  const [markdownContent, setMarkdownContent] = useState<string | null>(null);

  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // Load reports on mount
  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      const result = await listResearchReports();
      setReports(result.reports);
      if (result.reports.length > 0 && !selectedReport) {
        setSelectedReport(result.reports[0]);
      }
    } catch (err) {
      console.error("Failed to load reports:", err);
    }
  };

  const handleStartResearch = async () => {
    setLoading(true);
    setLoadingStatus("Loading research report...");
    setError(null);

    try {
      // Simulate a brief loading state for better UX
      await new Promise((resolve) => setTimeout(resolve, 500));
      
      const result = await getResearchMarkdown();
      setMarkdownContent(result.content);
      setLoadingStatus("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load research");
    } finally {
      setLoading(false);
      setLoadingStatus("");
    }
  };

  const toggleGenre = (genre: string) => {
    setSelectedGenres((prev) =>
      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]
    );
  };

  const togglePlatform = (platform: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform]
    );
  };

  const clearFilters = () => {
    setSelectedGenres([]);
    setSelectedPlatforms([]);
  };

  // Filter novels by selected genres/platforms
  const filteredNovels = selectedReport
    ? selectedReport.trending_novels.filter((novel) => {
        const genreMatch =
          selectedGenres.length === 0 ||
          selectedGenres.some((g) =>
            novel.genre.toLowerCase().includes(g.toLowerCase())
          );
        const platformMatch =
          selectedPlatforms.length === 0 ||
          selectedPlatforms.some((p) =>
            novel.platform.toLowerCase().includes(p.toLowerCase())
          );
        return genreMatch && platformMatch;
      })
    : [];

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
                  className="text-sky-600 font-medium text-sm"
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
                  className="text-gray-600 hover:text-gray-800 font-medium text-sm"
                >
                  Editor
                </a>
              </nav>
            </div>

          </div>
        </div>
      </header>

      {/* Hero Section */}
      {selectedReport && (
        <div className="bg-gradient-to-r from-sky-400 via-blue-400 to-indigo-400 text-white">
          <div className="max-w-7xl mx-auto px-4 py-12">
            <div className="flex flex-col md:flex-row items-center gap-8">
              <div className="flex-1">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/20 rounded-full text-sm font-medium mb-4">
                  <Flame size={14} />
                  Latest Research
                </div>
                <h2 className="text-3xl md:text-4xl font-bold mb-4">
                  {selectedReport.title}
                </h2>
                <p className="text-white/90 text-lg mb-6 max-w-xl">
                  {selectedReport.summary ||
                    "Discover trending web novels, genre insights, and trailer inspiration across major platforms."}
                </p>
                <button
                  onClick={() =>
                    document
                      .getElementById("novels-section")
                      ?.scrollIntoView({ behavior: "smooth" })
                  }
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-white text-sky-600 rounded-full font-semibold hover:bg-gray-100 transition-colors shadow-lg"
                >
                  <Play size={16} fill="currentColor" />
                  Explore Novels
                </button>
              </div>

              {/* Featured Covers */}
              <div className="flex gap-3">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className={`w-24 h-36 bg-gradient-to-br from-white/30 to-white/10 rounded-xl shadow-xl backdrop-blur-sm flex items-center justify-center ${
                      i === 2 ? "scale-110 z-10" : "opacity-80"
                    }`}
                  >
                    <BookOpen className="text-white/60" size={28} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
            {error}
          </div>
        )}

        {/* Report Selector & Filters */}
        {reports.length > 0 && (
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <select
              value={selectedReport?.id || ""}
              onChange={(e) => {
                const report = reports.find((r) => r.id === e.target.value);
                setSelectedReport(report || null);
              }}
              className="flex-1 bg-white border border-gray-200 rounded-xl px-4 py-2.5 text-gray-800 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              {reports.map((report) => (
                <option key={report.id} value={report.id}>
                  {report.title} -{" "}
                  {new Date(report.created_at).toLocaleDateString()}
                </option>
              ))}
            </select>

            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-4 py-2.5 rounded-xl font-medium transition-all flex items-center justify-center gap-2 border ${
                showFilters ||
                selectedGenres.length > 0 ||
                selectedPlatforms.length > 0
                  ? "bg-sky-500 text-white border-sky-500"
                  : "bg-white text-gray-700 border-gray-200 hover:border-sky-500"
              }`}
            >
              <Filter size={18} />
              Filters
              {(selectedGenres.length > 0 || selectedPlatforms.length > 0) && (
                <span className="px-1.5 py-0.5 bg-white/20 rounded text-xs">
                  {selectedGenres.length + selectedPlatforms.length}
                </span>
              )}
            </button>
          </div>
        )}

        {/* Filters Panel */}
        {showFilters && (
          <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-gray-800">Filter Results</h3>
              {(selectedGenres.length > 0 || selectedPlatforms.length > 0) && (
                <button
                  onClick={clearFilters}
                  className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
                >
                  <X size={14} />
                  Clear all
                </button>
              )}
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <div className="text-sm text-gray-500 font-medium mb-2">
                  Genres
                </div>
                <div className="flex flex-wrap gap-2">
                  {RESEARCH_GENRES.map((genre) => (
                    <button
                      key={genre.value}
                      onClick={() => toggleGenre(genre.value)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all border ${
                        selectedGenres.includes(genre.value)
                          ? "bg-sky-500 text-white border-sky-500"
                          : "bg-white text-gray-600 border-gray-200 hover:border-sky-500"
                      }`}
                    >
                      {genre.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <div className="text-sm text-gray-500 font-medium mb-2">
                  Platforms
                </div>
                <div className="flex flex-wrap gap-2">
                  {RESEARCH_PLATFORMS.map((platform) => (
                    <button
                      key={platform.value}
                      onClick={() => togglePlatform(platform.value)}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all border ${
                        selectedPlatforms.includes(platform.value)
                          ? "bg-purple-500 text-white border-purple-500"
                          : "bg-white text-gray-600 border-gray-200 hover:border-purple-500"
                      }`}
                    >
                      {platform.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Content Sections */}
        {selectedReport && (
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Main Content - 2 columns */}
            <div className="lg:col-span-2 space-y-6">
              {/* Genre Insights */}
              <DropdownSection
                title="New Releases"
                count={selectedReport.genres.length}
                icon={<Flame className="text-sky-500" size={22} />}
                defaultOpen={true}
              >
                <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {selectedReport.genres.map((genre, idx) => (
                    <GenreCard key={idx} genre={genre} />
                  ))}
                </div>
              </DropdownSection>

              {/* Trending Novels */}
              <div id="novels-section">
                <DropdownSection
                  title="Trending Novels"
                  count={filteredNovels.length}
                  icon={<Star className="text-sky-500" size={22} />}
                  defaultOpen={true}
                >
                  <div className="mt-4 space-y-4">
                    {filteredNovels.map((novel, idx) => (
                      <NovelCard key={idx} novel={novel} />
                    ))}
                  </div>
                  {filteredNovels.length === 0 && (
                    <div className="mt-4 text-center text-gray-500 py-8">
                      No novels match your filters. Try adjusting your
                      selection.
                    </div>
                  )}
                </DropdownSection>
              </div>
            </div>

            {/* Sidebar - 1 column */}
            <div className="space-y-6">
              {/* Announcements / Trailer Ideas */}
              <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
                <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100">
                  <Megaphone className="text-purple-500" size={20} />
                  <h3 className="font-bold text-gray-800">Trailer Ideas</h3>
                </div>
                <div className="space-y-4">
                  {selectedReport.trailer_suggestions
                    .slice(0, 5)
                    .map((idea, idx) => (
                      <div
                        key={idx}
                        className="flex gap-3 pb-4 border-b border-gray-50 last:border-0 last:pb-0"
                      >
                        <div className="w-10 h-10 bg-gradient-to-br from-purple-400 to-pink-400 rounded-lg flex items-center justify-center flex-shrink-0">
                          <Film className="text-white" size={16} />
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-800 text-sm">
                            {idea.title}
                          </h4>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {idea.target_emotion} • {idea.suggested_music_style}
                          </p>
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Platform Analysis */}
              <div className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
                <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100">
                  <BookOpen className="text-blue-500" size={20} />
                  <h3 className="font-bold text-gray-800">Platforms</h3>
                </div>
                <div className="space-y-2">
                  {selectedReport.platforms_analyzed.map((platform, idx) => (
                    <div
                      key={idx}
                      className="px-3 py-2 bg-gray-50 rounded-lg text-sm text-gray-700 hover:bg-gray-100 transition-colors cursor-pointer"
                    >
                      {platform}
                    </div>
                  ))}
                </div>
              </div>

              {/* Report Meta */}
              <div className="text-center text-gray-400 text-sm flex items-center justify-center gap-2">
                <Clock size={14} />
                {new Date(selectedReport.created_at).toLocaleString()}
              </div>
            </div>
          </div>
        )}

        {/* Markdown Report Display */}
        {markdownContent && !loading && (
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <BookOpen className="text-sky-500" size={22} />
                <span className="font-bold text-lg text-gray-800">Research Report</span>
              </div>
              <button
                onClick={() => setMarkdownContent(null)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            <div className="p-6 prose prose-lg max-w-none prose-headings:text-gray-800 prose-p:text-gray-600 prose-strong:text-gray-700 prose-table:text-sm">
              <MarkdownRenderer content={markdownContent} />
            </div>
          </div>
        )}

        {/* Empty State - Just Start Research Button */}
        {!selectedReport && !markdownContent && !loading && (
          <div className="flex items-center justify-center min-h-[60vh]">
            <button
              onClick={handleStartResearch}
              className="px-8 py-4 bg-gradient-to-r from-sky-400 to-blue-500 hover:from-sky-500 hover:to-blue-600 text-white rounded-full font-semibold text-lg transition-all shadow-lg hover:shadow-xl hover:scale-105"
            >
              Start Research
            </button>
          </div>
        )}

        {/* Loading State - Research Progress */}
        {!selectedReport && !markdownContent && loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="bg-white rounded-2xl border border-gray-200 shadow-lg p-8 max-w-md w-full">
              {/* Animated Icon */}
              <div className="flex justify-center mb-6">
                <div className="relative">
                  <div className="w-20 h-20 bg-gradient-to-br from-sky-100 to-blue-100 rounded-full flex items-center justify-center">
                    <Sparkles className="text-sky-500" size={36} />
                  </div>
                  <div className="absolute inset-0 w-20 h-20 border-4 border-sky-400 border-t-transparent rounded-full animate-spin"></div>
                </div>
              </div>

              {/* Title */}
              <h3 className="text-xl font-bold text-gray-800 text-center mb-2">
                Researching Web Novels
              </h3>
              <p className="text-gray-500 text-center text-sm mb-6">
                Manus AI is analyzing trends across platforms
              </p>

              {/* Progress Steps */}
              <div className="space-y-3 mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                    <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <span className="text-gray-700 text-sm">Task submitted to Manus</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 bg-sky-500 rounded-full flex items-center justify-center">
                    <Loader2 className="w-4 h-4 text-white animate-spin" />
                  </div>
                  <span className="text-gray-700 text-sm">Analyzing market trends...</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 bg-gray-200 rounded-full flex items-center justify-center">
                    <span className="text-gray-400 text-xs">3</span>
                  </div>
                  <span className="text-gray-400 text-sm">Generate report</span>
                </div>
              </div>

              {/* Status Message */}
              <div className="bg-sky-50 border border-sky-200 rounded-lg p-3">
                <p className="text-sky-800 text-sm text-center font-medium">
                  {loadingStatus || "Initializing..."}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
