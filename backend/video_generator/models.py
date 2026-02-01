"""
Pydantic models for video generation pipeline.
Adapted for the novel-to-trailer keyframe structure.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class KeyframeScene(BaseModel):
    """Represents a single keyframe to be converted to video."""
    kf_id: str = Field(..., description="Unique keyframe identifier")
    beat_id: str = Field(..., description="Beat identifier")
    order_in_beat: int = Field(1, description="Order within the beat")
    suggested_duration_sec: float = Field(8.0, description="Suggested duration in seconds")
    shot_type: str = Field("", description="Shot type (ECU, CU, MS, MLS, LS, ELS)")
    camera_angle: str = Field("", description="Camera angle description")
    action: str = Field("", description="Action happening in the scene")
    emotion_tags: List[str] = Field(default_factory=list, description="Emotion tags")
    characters: List[str] = Field(default_factory=list, description="Characters in scene")
    dialogue_or_text: str = Field("", description="Dialogue or text overlay")
    image_prompt: str = Field("", description="Image generation prompt")
    image_path: Optional[str] = Field(None, description="Path to keyframe image")


class KeyframeInput(BaseModel):
    """Input model for the video generation pipeline."""
    novel_id: str = Field("", description="Novel identifier")
    title: str = Field("Unknown Novel", description="Novel title")
    global_style: str = Field("", description="Global visual style")
    keyframes: List[KeyframeScene] = Field(default_factory=list)


class GeneratedClip(BaseModel):
    """Represents a generated video clip."""
    clip_id: str
    kf_id: str
    frame_id: int
    duration: float
    video_url: str
    thumbnail_url: str
    prompt_used: str = ""


class VideoGenerationOutput(BaseModel):
    """Output model for the video generation pipeline."""
    status: str = "completed"
    title: str = ""
    generated_clips: List[GeneratedClip] = Field(default_factory=list)
