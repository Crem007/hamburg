"""
Video Concatenation Script for Trailer Assembly

This script assembles keyframe videos into a final trailer based on trailer_script.json.
It follows the beat structure (hook -> conflict -> escalation -> cliffhanger) and can
add text overlays for dialogue/captions.

Usage:
    python 008_concat_videos.py
    python 008_concat_videos.py --with-fade
    python 008_concat_videos.py --with-subtitles
    python 008_concat_videos.py --with-title-card

Requirements:
    - ffmpeg installed on the system
    - trailer_script.json with beat structure
    - video_generation.json with generated clips info
"""

import os
import json
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Beat:
    """Represents a trailer beat (section)."""
    beat_id: str
    role: str
    duration_sec: float
    dialogue_or_text: List[str]
    key_moments: List[str]
    logline: str


@dataclass
class ClipInfo:
    """Represents a video clip."""
    kf_id: str
    beat_id: str
    video_path: str
    duration: float


def load_trailer_script(json_path: Path) -> dict:
    """Load trailer script from JSON file."""
    if not json_path.exists():
        raise FileNotFoundError(f"trailer_script.json not found at {json_path}")
    return json.loads(json_path.read_text(encoding="utf-8"))


def load_video_generation_data(json_path: Path) -> dict:
    """Load video generation data from JSON file."""
    if not json_path.exists():
        raise FileNotFoundError(f"video_generation.json not found at {json_path}")
    return json.loads(json_path.read_text(encoding="utf-8"))


def get_video_duration(video_path: str) -> float:
    """Get video duration using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def get_video_resolution(video_path: str) -> tuple:
    """Get video resolution using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    w, h = result.stdout.strip().split(",")
    return int(w), int(h)


def organize_clips_by_beat(clips: List[dict], beats: List[dict]) -> Dict[str, List[ClipInfo]]:
    """Organize clips by their beat ID based on keyframe naming convention (KF_B{beat}_xx)."""
    beat_clips = {beat["beat_id"]: [] for beat in beats}

    for clip in clips:
        kf_id = clip.get("kf_id", "")
        video_path = clip.get("video_url", "")

        if not video_path or not Path(video_path).exists():
            continue

        # Extract beat ID from keyframe ID (e.g., KF_B1_01 -> B1)
        parts = kf_id.split("_")
        if len(parts) >= 2:
            beat_id = parts[1]  # B1, B2, B3, B4
            if beat_id in beat_clips:
                beat_clips[beat_id].append(ClipInfo(
                    kf_id=kf_id,
                    beat_id=beat_id,
                    video_path=video_path,
                    duration=get_video_duration(video_path)
                ))

    # Sort clips within each beat by their sequence number
    for beat_id in beat_clips:
        beat_clips[beat_id].sort(key=lambda c: c.kf_id)

    return beat_clips


def get_first_video_resolution(clips: List[dict]) -> tuple:
    """Get resolution from the first available video clip."""
    for clip in clips:
        video_path = clip.get("video_url", "")
        if video_path and Path(video_path).exists():
            try:
                return get_video_resolution(video_path)
            except Exception:
                pass
    return 1280, 720  # Default fallback


def create_title_card(title: str, output_path: str, duration: float = 2.0,
                      width: int = None, height: int = None) -> str:
    """Create a title card video using ffmpeg, matching source video dimensions."""
    # Use provided dimensions or default
    w = width or 1280
    h = height or 720

    # Escape special characters for ffmpeg drawtext
    escaped_title = title.replace("'", "'\\''").replace(":", "\\:")

    # Adjust font size based on resolution
    font_size = max(24, min(w, h) // 15)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={w}x{h}:d={duration}",
        "-vf", f"drawtext=text='{escaped_title}':fontcolor=white:fontsize={font_size}:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264",
        "-preset", "fast",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Failed to create title card: {result.stderr}")
        return None
    return output_path


def create_text_card(text: str, output_path: str, duration: float = 2.0,
                     width: int = None, height: int = None, bg_color: str = "black") -> str:
    """Create a text overlay card matching source video dimensions."""
    w = width or 1280
    h = height or 720

    escaped_text = text.replace("'", "'\\''").replace(":", "\\:")

    # Adjust font size based on resolution
    font_size = max(20, min(w, h) // 20)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg_color}:s={w}x{h}:d={duration}",
        "-vf", f"drawtext=text='{escaped_text}':fontcolor=white:fontsize={font_size}:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264",
        "-preset", "fast",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Failed to create text card: {result.stderr}")
        return None
    return output_path


def add_subtitle_to_video(input_path: str, output_path: str, text: str,
                          position: str = "bottom") -> str:
    """Add subtitle text overlay to a video."""
    escaped_text = text.replace("'", "'\\''").replace(":", "\\:")

    # Position: bottom = y=h-th-50, center = y=(h-text_h)/2
    y_pos = "h-text_h-50" if position == "bottom" else "(h-text_h)/2"

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", f"drawtext=text='{escaped_text}':fontcolor=white:fontsize=28:x=(w-text_w)/2:y={y_pos}:borderw=2:bordercolor=black",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Failed to add subtitle: {result.stderr}")
        return None
    return output_path


def normalize_video(input_path: str, output_path: str, target_width: int = None, target_height: int = None) -> bool:
    """
    Normalize video to consistent format for concatenation.
    If target dimensions not specified, keeps original dimensions.
    """
    if target_width and target_height:
        # Scale to target dimensions while preserving aspect ratio
        vf = f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    else:
        # Just normalize format without changing dimensions
        vf = "setsar=1"

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-an",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def create_concat_file(video_paths: List[str], concat_file_path: Path) -> None:
    """Create a concat demuxer file for ffmpeg."""
    with open(concat_file_path, "w") as f:
        for path in video_paths:
            escaped_path = path.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")


def concat_videos_simple(video_paths: List[str], output_path: str, temp_dir: Path) -> bool:
    """Concatenate videos using concat demuxer."""
    concat_file = temp_dir / "concat_list.txt"
    create_concat_file(video_paths, concat_file)

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def concat_with_filter(video_paths: List[str], output_path: str, fade_duration: float = 0.5) -> bool:
    """Concatenate videos with optional crossfade transitions."""
    if len(video_paths) < 2:
        # Single video, just copy
        cmd = ["ffmpeg", "-y", "-i", video_paths[0], "-c", "copy", output_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    # Get durations
    durations = [get_video_duration(p) for p in video_paths]

    # Build xfade filter chain
    filter_parts = []
    current_label = "[0:v]"
    total_offset = 0

    for i in range(1, len(video_paths)):
        offset = total_offset + durations[i-1] - fade_duration
        out_label = "[outv]" if i == len(video_paths) - 1 else f"[v{i}]"

        filter_parts.append(
            f"{current_label}[{i}:v]xfade=transition=fade:duration={fade_duration}:offset={offset:.3f}{out_label}"
        )
        current_label = out_label
        total_offset = offset

    filter_complex = ";".join(filter_parts)

    cmd = ["ffmpeg", "-y"]
    for path in video_paths:
        cmd.extend(["-i", path])
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        output_path
    ])

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Assemble trailer from keyframe videos")
    parser.add_argument("--with-fade", action="store_true", help="Add fade transitions between clips")
    parser.add_argument("--fade-duration", type=float, default=0.5, help="Fade duration in seconds")
    parser.add_argument("--with-subtitles", action="store_true", help="Add dialogue/text overlays from script")
    parser.add_argument("--with-title-card", action="store_true", help="Add title card at beginning")
    parser.add_argument("--with-end-card", action="store_true", help="Add end card")
    parser.add_argument("--normalize", action="store_true", help="Normalize all videos first")
    args = parser.parse_args()

    # Setup paths
    base_dir = Path(__file__).resolve().parent.parent
    trailer_script_path = base_dir / "data" / "trailer_script.json"
    video_gen_path = base_dir / "output" / "video_generation.json"
    output_dir = base_dir / "output" / "final"
    temp_dir = base_dir / "output" / "temp"

    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print("[INFO] Loading trailer script...")
    trailer_script = load_trailer_script(trailer_script_path)

    print("[INFO] Loading video generation data...")
    video_data = load_video_generation_data(video_gen_path)

    title = trailer_script.get("title", "Trailer")
    max_duration = trailer_script.get("max_duration_sec", 30)
    beats = trailer_script.get("beats", [])
    clips = video_data.get("generated_clips", [])

    print(f"[INFO] Title: {title}")
    print(f"[INFO] Target duration: {max_duration}s")
    print(f"[INFO] Beats: {len(beats)}")
    print(f"[INFO] Available clips: {len(clips)}")

    # Organize clips by beat
    beat_clips = organize_clips_by_beat(clips, beats)

    # Get source video resolution (for title cards etc.)
    source_width, source_height = get_first_video_resolution(clips)
    print(f"[INFO] Source resolution: {source_width}x{source_height}")

    # Print beat structure
    print("\n[INFO] Beat structure:")
    for beat in beats:
        beat_id = beat["beat_id"]
        role = beat["role"]
        clips_in_beat = beat_clips.get(beat_id, [])
        total_dur = sum(c.duration for c in clips_in_beat)
        print(f"  {beat_id} ({role}): {len(clips_in_beat)} clips, {total_dur:.1f}s")
        for clip in clips_in_beat:
            print(f"    - {clip.kf_id}: {clip.duration:.1f}s")

    # Build final video sequence
    final_sequence = []
    subtitle_map = {}  # video_path -> subtitle text

    # Add title card if requested
    if args.with_title_card:
        title_card_path = str(temp_dir / "title_card.mp4")
        if create_title_card(title, title_card_path, duration=2.0, width=source_width, height=source_height):
            final_sequence.append(title_card_path)
            print("[INFO] Added title card")

    # Process each beat in order
    for beat in beats:
        beat_id = beat["beat_id"]
        role = beat["role"]
        dialogue = beat.get("dialogue_or_text", [])

        clips_in_beat = beat_clips.get(beat_id, [])
        if not clips_in_beat:
            print(f"[WARN] No clips for beat {beat_id}")
            continue

        print(f"\n[INFO] Processing beat {beat_id} ({role})...")

        # Add clips for this beat
        for i, clip in enumerate(clips_in_beat):
            video_path = clip.video_path

            # Normalize if requested (preserving original dimensions)
            if args.normalize:
                norm_path = str(temp_dir / f"norm_{clip.kf_id}.mp4")
                if normalize_video(video_path, norm_path, target_width=source_width, target_height=source_height):
                    video_path = norm_path

            # Add subtitle if requested and available
            if args.with_subtitles and dialogue:
                # Distribute dialogue across clips in this beat
                if i < len(dialogue):
                    text = dialogue[i]
                    # Remove "TEXT: " prefix if present
                    if text.startswith("TEXT: "):
                        text = text[6:]
                    sub_path = str(temp_dir / f"sub_{clip.kf_id}.mp4")
                    result = add_subtitle_to_video(video_path, sub_path, text)
                    if result:
                        video_path = result
                        print(f"    Added subtitle: {text[:30]}...")

            final_sequence.append(video_path)

    # Add end card if requested
    if args.with_end_card:
        end_text = "Read the full story"
        end_card_path = str(temp_dir / "end_card.mp4")
        if create_text_card(end_text, end_card_path, duration=2.0, width=source_width, height=source_height):
            final_sequence.append(end_card_path)
            print("[INFO] Added end card")

    if not final_sequence:
        print("[ERROR] No videos to concatenate")
        return

    # Calculate total duration
    total_duration = sum(get_video_duration(p) for p in final_sequence)
    print(f"\n[INFO] Total clips: {len(final_sequence)}")
    print(f"[INFO] Total duration: {total_duration:.1f}s (target: {max_duration}s)")

    # Generate output filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
    output_path = str(output_dir / f"{safe_title}_trailer.mp4")

    # Concatenate
    print(f"\n[INFO] Assembling final trailer: {output_path}")

    if args.with_fade:
        # Need to normalize first for filter-based concat (keep original dimensions)
        print("[INFO] Normalizing videos for fade transitions (preserving original dimensions)...")
        normalized = []
        for i, path in enumerate(final_sequence):
            norm_path = str(temp_dir / f"final_norm_{i:03d}.mp4")
            # Pass source dimensions to maintain consistent size across all clips
            if normalize_video(path, norm_path, target_width=source_width, target_height=source_height):
                normalized.append(norm_path)
            else:
                normalized.append(path)
        success = concat_with_filter(normalized, output_path, args.fade_duration)
    else:
        success = concat_videos_simple(final_sequence, output_path, temp_dir)

    if success:
        final_duration = get_video_duration(output_path)
        file_size = Path(output_path).stat().st_size / (1024 * 1024)
        final_width, final_height = get_video_resolution(output_path)

        print("\n" + "="*60)
        print("TRAILER ASSEMBLY COMPLETE")
        print("="*60)
        print(f"Title:          {title}")
        print(f"Output:         {output_path}")
        print(f"Resolution:     {final_width}x{final_height}")
        print(f"Duration:       {final_duration:.2f}s")
        print(f"File size:      {file_size:.2f} MB")
        print(f"Beat count:     {len(beats)}")
        print(f"Clip count:     {len(final_sequence)}")
        print("="*60)

        # Print beat breakdown
        print("\nBeat breakdown:")
        for beat in beats:
            print(f"  {beat['beat_id']} ({beat['role']}): {beat.get('logline', '')[:50]}...")
    else:
        print("\n[ERROR] Trailer assembly failed")


if __name__ == "__main__":
    main()
