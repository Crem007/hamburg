"""
Veo Client for video generation using Google Generative AI.
Extracted from viral-launch-video-main/backend/video_generator/veo_client.py
"""

from typing import Optional
import time
from pathlib import Path

from google import genai
from google.genai import types, errors as genai_errors


class VeoClient:
    """Client for Google Veo video generation API."""

    def __init__(self, api_key: str, image_base_path: Optional[str] = None):
        """Initialize the Veo client.

        Args:
            api_key: Google API key for authentication.
            image_base_path: Optional base directory for resolving relative image paths.
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.image_base_path = image_base_path
        # Veo 3.1 (latest) for high quality video generation
        self.model = "veo-3.1-generate-preview"

    def generate_clip(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        output_dir: Optional[str] = None,
        video_id: Optional[str] = None,
        duration_seconds: int = 8,
    ) -> str:
        """Generate a video clip using Veo.

        Args:
            prompt: Text prompt describing the video content.
            image_url: Optional URL or path to an image to use as starting frame.
            output_dir: Directory to save the generated video.
            video_id: Unique identifier for the video file.
            duration_seconds: Duration of the generated video (max 8s).

        Returns:
            Path to the generated video file.
        """
        print(f"[VEO] Generating clip: {video_id}")
        print(f"[VEO] Prompt: {prompt[:100]}...")

        try:
            # Prepare image if URL or path is provided
            image_obj = None

            if image_url:
                # If it's an HTTP(S) URL
                if str(image_url).startswith(("http://", "https://")):
                    try:
                        image_obj = types.Image.from_file(location=image_url)
                        print(f"[VEO] Image loaded from URL: {image_url}")
                    except Exception as url_error:
                        print(f"[VEO] Direct URL loading failed: {url_error}")
                        # Could implement download fallback here if needed
                        image_obj = None
                else:
                    # Treat as local path
                    image_path = Path(str(image_url))

                    # If it's a relative path and base path is set, join them
                    if not image_path.is_absolute() and self.image_base_path:
                        image_path = Path(self.image_base_path) / str(image_url).lstrip("/")

                    if image_path.exists():
                        image_obj = types.Image.from_file(location=str(image_path))
                        print(f"[VEO] Image loaded from local path: {image_path}")
                    else:
                        print(f"[VEO] Warning: Image not found at {image_path}")

            # Create video generation operation
            print(f"[VEO] Starting video generation with model: {self.model}")
            try:
                operation = self.client.models.generate_videos(
                    model=self.model,
                    prompt=prompt,
                    image=image_obj,
                    config=types.GenerateVideosConfig(
                        number_of_videos=1,
                        duration_seconds=min(duration_seconds, 8),  # Max 8s
                    ),
                )
            except genai_errors.ClientError as e:
                # If image is rejected, retry without image
                if "Unable to process input image" in str(e):
                    print("[VEO] Image rejected, retrying without image reference...")
                    operation = self.client.models.generate_videos(
                        model=self.model,
                        prompt=prompt,
                        image=None,
                        config=types.GenerateVideosConfig(
                            number_of_videos=1,
                            duration_seconds=min(duration_seconds, 8),
                        ),
                    )
                else:
                    raise

            # Poll until completion
            print(f"[VEO] Operation started: {operation.name}")
            poll_count = 0
            while not operation.done:
                poll_count += 1
                print(f"[VEO] Polling... ({poll_count * 20}s elapsed)")
                time.sleep(20)
                operation = self.client.operations.get(operation)

            print("[VEO] Generation complete!")

            # Download and save the video
            video = operation.response.generated_videos[0].video
            self.client.files.download(file=video)

            if video_id:
                video_filename = f"{video_id}.mp4"
            else:
                timestamp = int(time.time())
                video_filename = f"video_{timestamp}.mp4"

            output_path = Path(output_dir) if output_dir else Path(".")
            output_path.mkdir(parents=True, exist_ok=True)
            video_path = output_path / video_filename
            video.save(str(video_path))

            print(f"[VEO] Saved: {video_path}")
            return str(video_path)

        except Exception as e:
            print(f"[VEO] Error generating video: {e}")
            raise
