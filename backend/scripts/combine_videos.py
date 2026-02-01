"""
Combine Keyframe Videos into a Single Trailer

This script concatenates all keyframe video clips into a single trailer video
using ffmpeg.

Usage:
    python combine_videos.py

Requirements:
    - ffmpeg installed and in PATH
    - Keyframe videos in keyframe_videos_02/ directory
"""

import subprocess
import tempfile
from pathlib import Path


def get_sorted_video_files(video_dir: Path) -> list[Path]:
    """Get all video files sorted by their keyframe ID."""
    video_files = sorted(video_dir.glob("KF_*.mp4"))
    return video_files


def combine_videos(video_files: list[Path], output_path: Path) -> bool:
    """
    Combine multiple video files into a single video using ffmpeg concat demuxer.

    Args:
        video_files: List of video file paths to concatenate
        output_path: Path for the output combined video

    Returns:
        True if successful, False otherwise
    """
    if not video_files:
        print("[ERROR] No video files to combine")
        return False

    # Create a temporary file listing all videos
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for video_path in video_files:
            # ffmpeg concat demuxer requires escaped paths
            escaped_path = str(video_path).replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
        concat_list_path = f.name

    print(f"[INFO] Concatenating {len(video_files)} videos...")
    for vf in video_files:
        print(f"  - {vf.name}")

    try:
        # Use ffmpeg to concatenate videos
        # -f concat: use concat demuxer
        # -safe 0: allow absolute paths
        # -i: input file list
        # -c copy: copy streams without re-encoding (fast)
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            str(output_path)
        ]

        print(f"[INFO] Running: {' '.join(cmd[:6])}...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"[ERROR] ffmpeg failed: {result.stderr}")
            return False

        print(f"[SUCCESS] Combined video saved to: {output_path}")
        return True

    except FileNotFoundError:
        print("[ERROR] ffmpeg not found. Please install ffmpeg and add it to PATH.")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to combine videos: {e}")
        return False
    finally:
        # Clean up temp file
        Path(concat_list_path).unlink(missing_ok=True)


def main():
    """Main entry point."""
    base_dir = Path(__file__).resolve().parent.parent
    video_dir = base_dir / "output" / "keyframe_videos_02"
    output_dir = base_dir / "output"

    if not video_dir.exists():
        print(f"[ERROR] Video directory not found: {video_dir}")
        return

    # Get sorted video files
    video_files = get_sorted_video_files(video_dir)

    if not video_files:
        print(f"[ERROR] No video files found in {video_dir}")
        return

    print(f"[INFO] Found {len(video_files)} video files")

    # Combine into trailer
    output_path = output_dir / "combined_trailer.mp4"
    success = combine_videos(video_files, output_path)

    if success:
        # Print file size
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"\n[INFO] Output file size: {size_mb:.2f} MB")

    print("\n" + "="*60)
    print("COMBINATION COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
