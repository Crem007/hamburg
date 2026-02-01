"""
Video generation pipeline for converting keyframes to video clips.
Simplified version that doesn't require pydantic-graph dependency.
"""

import asyncio
from typing import Optional, List
from pathlib import Path

from .models import KeyframeInput, KeyframeScene, VideoGenerationOutput, GeneratedClip
from .veo_client import VeoClient


def build_video_prompt(kf: KeyframeScene, global_style: str) -> str:
    """Build a prompt for video generation from keyframe data.

    For video generation, we focus on:
    - Action and movement
    - Camera motion
    - Atmosphere and mood
    """
    parts = []

    # Style context (shorter for video)
    if global_style:
        parts.append(f"Visual style: {global_style[:200]}")

    # Shot and camera
    if kf.shot_type:
        parts.append(f"Shot type: {kf.shot_type}")
    if kf.camera_angle:
        parts.append(f"Camera: {kf.camera_angle}")

    # Main action (key for video)
    if kf.action:
        parts.append(f"Action: {kf.action}")

    # Mood
    if kf.emotion_tags:
        parts.append(f"Mood: {', '.join(kf.emotion_tags)}")

    # Add some of the detailed description
    if kf.image_prompt:
        parts.append(f"Scene details: {kf.image_prompt[:300]}")

    # Video-specific instructions
    parts.append("Cinematic motion, smooth camera movement, atmospheric lighting.")

    return " ".join(parts)


async def process_keyframe(
    veo_client: VeoClient,
    kf: KeyframeScene,
    global_style: str,
    output_dir: Path,
    idx: int,
) -> Optional[GeneratedClip]:
    """Process a single keyframe and generate video clip."""
    print(f"[Pipeline] Processing keyframe: {kf.kf_id}")

    # Build prompt
    prompt = build_video_prompt(kf, global_style)

    # Generate video using Veo (blocking call in thread)
    try:
        video_path = await asyncio.to_thread(
            veo_client.generate_clip,
            prompt,
            image_url=kf.image_path,
            output_dir=str(output_dir),
            video_id=kf.kf_id,
            duration_seconds=min(int(kf.suggested_duration_sec), 8),
        )

        return GeneratedClip(
            clip_id=f"clip_{idx:02d}",
            kf_id=kf.kf_id,
            frame_id=idx,
            duration=kf.suggested_duration_sec,
            video_url=video_path,
            thumbnail_url=kf.image_path or "",
            prompt_used=prompt,
        )
    except Exception as e:
        print(f"[Pipeline] Failed to generate video for {kf.kf_id}: {e}")
        return None


async def run_keyframe_pipeline(
    keyframe_input: KeyframeInput,
    api_key: str,
    output_dir: str,
    image_base_path: Optional[str] = None,
    parallel: bool = False,
) -> VideoGenerationOutput:
    """Run the video generation pipeline for all keyframes.

    Args:
        keyframe_input: Input data containing keyframes.
        api_key: Google API key for Veo.
        output_dir: Directory to save generated videos.
        image_base_path: Base path for resolving image paths.
        parallel: If True, generate videos in parallel (may hit rate limits).

    Returns:
        VideoGenerationOutput with all generated clips.
    """
    print(f"[Pipeline] Starting video generation for: {keyframe_input.title}")
    print(f"[Pipeline] Keyframes to process: {len(keyframe_input.keyframes)}")

    # Initialize Veo client
    veo_client = VeoClient(api_key=api_key, image_base_path=image_base_path)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generated_clips: List[GeneratedClip] = []

    if parallel:
        # Parallel processing (may hit rate limits)
        tasks = [
            process_keyframe(
                veo_client, kf, keyframe_input.global_style, output_path, idx
            )
            for idx, kf in enumerate(keyframe_input.keyframes, start=1)
        ]
        results = await asyncio.gather(*tasks)
        generated_clips = [clip for clip in results if clip is not None]
    else:
        # Sequential processing (safer for rate limits)
        for idx, kf in enumerate(keyframe_input.keyframes, start=1):
            # Check if video already exists
            video_path = output_path / f"{kf.kf_id}.mp4"
            if video_path.exists():
                print(f"[Pipeline] Video exists for {kf.kf_id}, skipping...")
                generated_clips.append(GeneratedClip(
                    clip_id=f"clip_{idx:02d}",
                    kf_id=kf.kf_id,
                    frame_id=idx,
                    duration=kf.suggested_duration_sec,
                    video_url=str(video_path),
                    thumbnail_url=kf.image_path or "",
                    prompt_used="[existing]",
                ))
                continue

            clip = await process_keyframe(
                veo_client, kf, keyframe_input.global_style, output_path, idx
            )
            if clip:
                generated_clips.append(clip)

    print(f"[Pipeline] Generated {len(generated_clips)} video clips")

    return VideoGenerationOutput(
        status="completed",
        title=keyframe_input.title,
        generated_clips=generated_clips,
    )
