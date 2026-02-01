"use client";

/**
 * Launch page - Final output and distribution.
 * Step 3 of the novel-to-trailer pipeline.
 * Extracted from viral-launch-video-main.
 */

import { useState, useEffect } from "react";
import {
  CheckCircle,
  Download,
  Share2,
  Copy,
  Youtube,
  Twitter,
  Instagram,
  Play,
  Film,
} from "lucide-react";

interface LaunchData {
  title: string;
  final_video_url: string;
  thumbnail_url: string;
  metadata: {
    duration: number;
    format: string;
    resolution: string;
  };
  social_posts?: {
    platform: string;
    copy: string;
  }[];
}

export default function LaunchPage() {
  const [copied, setCopied] = useState(false);
  const [launchData, setLaunchData] = useState<LaunchData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Try to load launch.json, fallback to generated data
    (async () => {
      try {
        const response = await fetch("/launch.json");
        if (response.ok) {
          const data = await response.json();
          setLaunchData(data);
        } else {
          // Generate default launch data from video_generation.json
          const videoResponse = await fetch("/video_generation.json");
          if (videoResponse.ok) {
            const videoData = await videoResponse.json();
            const totalDuration = videoData.generated_clips.reduce(
              (acc: number, clip: any) => acc + clip.duration,
              0
            );
            setLaunchData({
              title: videoData.title || "Novel Trailer",
              final_video_url: "/videos/final_trailer.mp4",
              thumbnail_url: videoData.generated_clips[0]?.thumbnail_url || "",
              metadata: {
                duration: totalDuration,
                format: "MP4",
                resolution: "1080x1920",
              },
              social_posts: [
                {
                  platform: "TikTok",
                  copy: `Check out this epic trailer for "${videoData.title}"! #BookTok #NovelTrailer #MustRead`,
                },
                {
                  platform: "YouTube Shorts",
                  copy: `${videoData.title} - Official Trailer | Coming Soon`,
                },
                {
                  platform: "Instagram Reels",
                  copy: `The story that will keep you up all night... "${videoData.title}" #BookRecommendation`,
                },
              ],
            });
          }
        }
      } catch (e) {
        console.error("Failed to load launch data:", e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    // In a real implementation, this would download the rendered video
    const a = document.createElement("a");
    a.href = launchData?.final_video_url || "/videos/final_trailer.mp4";
    a.download = `${launchData?.title || "trailer"}.mp4`;
    a.click();
  };

  if (loading) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-zinc-950 text-white">
        <div className="animate-spin w-8 h-8 border-2 border-white border-t-transparent rounded-full"></div>
      </div>
    );
  }

  return (
    <div className="w-full min-h-screen bg-zinc-950 text-white py-12 px-4">
      <div className="max-w-4xl mx-auto flex flex-col items-center text-center">
        {/* Success Icon */}
        <div className="mb-6 relative">
          <div className="absolute inset-0 bg-green-500/20 blur-3xl rounded-full"></div>
          <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-600 rounded-full flex items-center justify-center border-4 border-zinc-950 shadow-2xl relative z-10">
            <CheckCircle className="w-8 h-8 text-black" strokeWidth={3} />
          </div>
        </div>

        <h1 className="text-3xl font-bold text-zinc-100 mb-2">
          Trailer Ready for Launch
        </h1>
        <p className="text-zinc-400 mb-8 max-w-xl">
          Your novel trailer has been generated and is ready for distribution
          across social media platforms.
        </p>

        {/* Video Preview */}
        <div className="w-full max-w-md aspect-[9/16] bg-black rounded-2xl border border-zinc-800 overflow-hidden shadow-2xl mb-8 relative group">
          {launchData?.thumbnail_url ? (
            <img
              src={launchData.thumbnail_url}
              alt="Trailer thumbnail"
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-zinc-900">
              <Film size={48} className="text-zinc-700" />
            </div>
          )}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-16 h-16 bg-white/20 backdrop-blur-md rounded-full flex items-center justify-center cursor-pointer hover:scale-110 transition-transform">
              <Play fill="white" className="text-white ml-1" size={24} />
            </div>
          </div>

          {/* Video info overlay */}
          <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 to-transparent">
            <p className="font-bold text-lg">{launchData?.title}</p>
            <p className="text-sm text-zinc-400">
              {launchData?.metadata.resolution} •{" "}
              {Math.round(launchData?.metadata.duration || 0)}s •{" "}
              {launchData?.metadata.format}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 w-full max-w-md mb-8">
          <button
            onClick={handleDownload}
            className="flex-1 px-6 py-3 bg-white text-black rounded-xl font-bold text-sm hover:bg-zinc-200 shadow-lg hover:scale-105 transition-all flex items-center justify-center gap-2"
          >
            <Download size={18} /> Download Video
          </button>
          <button className="flex-1 px-6 py-3 bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-xl font-bold text-sm hover:bg-zinc-800 transition-all flex items-center justify-center gap-2">
            <Share2 size={18} /> Share
          </button>
        </div>

        {/* Social Media Posts */}
        {launchData?.social_posts && launchData.social_posts.length > 0 && (
          <div className="w-full max-w-lg">
            <h2 className="text-lg font-bold mb-4 text-left">
              Ready-to-Post Captions
            </h2>
            <div className="space-y-3">
              {launchData.social_posts.map((post, idx) => (
                <div
                  key={idx}
                  className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 text-left"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-green-400">
                      {post.platform}
                    </span>
                    <button
                      onClick={() => handleCopy(post.copy)}
                      className="text-zinc-500 hover:text-white transition-colors"
                    >
                      <Copy size={16} />
                    </button>
                  </div>
                  <p className="text-sm text-zinc-300">{post.copy}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Social Links */}
        <div className="mt-8 flex items-center gap-4 text-zinc-500">
          <span className="text-xs font-medium uppercase tracking-widest">
            Direct Share
          </span>
          <div className="h-px w-8 bg-zinc-800"></div>
          <button className="hover:text-red-500 transition-colors">
            <Youtube size={20} />
          </button>
          <button className="hover:text-blue-400 transition-colors">
            <Twitter size={20} />
          </button>
          <button className="hover:text-pink-500 transition-colors">
            <Instagram size={20} />
          </button>
        </div>

        {/* Back to Editor */}
        <a
          href="/"
          className="mt-8 text-sm text-zinc-500 hover:text-white transition-colors"
        >
          ← Back to Editor
        </a>
      </div>

      {/* Copy notification */}
      {copied && (
        <div className="fixed bottom-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg animate-in fade-in">
          Copied to clipboard!
        </div>
      )}
    </div>
  );
}
