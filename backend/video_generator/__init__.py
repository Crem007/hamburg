"""
Video Generator Module

Generates video clips from keyframe images using Google Veo API.
Adapted from viral-launch-video-main for the novel-to-trailer pipeline.
"""

from .pipeline import run_keyframe_pipeline
from .veo_client import VeoClient
from .models import (
    KeyframeInput,
    KeyframeScene,
    VideoGenerationOutput,
    GeneratedClip,
)

__all__ = [
    "run_keyframe_pipeline",
    "VeoClient",
    "KeyframeInput",
    "KeyframeScene",
    "VideoGenerationOutput",
    "GeneratedClip",
]
