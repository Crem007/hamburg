"""
Keyframe to Video Generation Script using Google Veo API

This script converts keyframe images into video clips using Google's Veo model.
Supports both Gemini API and Vertex AI API.

Usage:
    python 007_generate_keyframe_videos.py
    python 007_generate_keyframe_videos.py --use-vertex

Requirements:
    - For Gemini API: GOOGLE_API_KEY in .env file
    - For Vertex AI: GOOGLE_CLOUD_PROJECT in .env + gcloud auth application-default login
    - Keyframe images in keyframe_images/ or keyframe_images_flux/ directory
    - keyframe_plan_styled.json with keyframe metadata
"""

import os
import json
import time
import asyncio
import base64
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from dotenv import load_dotenv

# Try to import both SDKs
try:
    from google import genai
    from google.genai import types, errors as genai_errors
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    import vertexai
    from vertexai.vision_models import ImageGenerationModel
    from vertexai.preview.vision_models import VideoCaptioningModel
    VERTEX_AVAILABLE = True
except ImportError:
    VERTEX_AVAILABLE = False


# ============================================================================
# VEO CLIENT - VERTEX AI VERSION
# ============================================================================

class VeoClientVertex:
    """Client for Google Veo video generation via Vertex AI using PredictLongRunning API."""

    def __init__(self, project_id: str, location: str = "us-central1"):
        """Initialize the Vertex AI Veo client.

        Args:
            project_id: Google Cloud project ID.
            location: Google Cloud region (default: us-central1).
        """
        self.project_id = project_id
        self.location = location
        self.api_endpoint = f"https://{location}-aiplatform.googleapis.com/v1"

        # Get credentials with proper scopes for Vertex AI
        from google.oauth2 import service_account
        import os

        creds_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        scopes = ["https://www.googleapis.com/auth/cloud-platform"]

        if creds_file and Path(creds_file).exists():
            self.credentials = service_account.Credentials.from_service_account_file(
                creds_file, scopes=scopes
            )
            print(f"[VERTEX] Using service account from: {creds_file}")
        else:
            import google.auth
            self.credentials, _ = google.auth.default(scopes=scopes)
            print(f"[VERTEX] Using default credentials")

        print(f"[VERTEX] Initialized with project: {project_id}, location: {location}")

    def _get_access_token(self) -> str:
        """Get a valid access token."""
        import google.auth.transport.requests
        request = google.auth.transport.requests.Request()
        self.credentials.refresh(request)
        return self.credentials.token

    def generate_clip(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        output_dir: str = ".",
        video_id: str = "video",
        duration_seconds: int = 8,
    ) -> Optional[str]:
        """Generate a video clip using Veo via Vertex AI PredictLongRunning API.

        Args:
            prompt: Text prompt describing the video content.
            image_path: Optional path to an image to use as starting frame.
            output_dir: Directory to save the generated video.
            video_id: Unique identifier for the video file.
            duration_seconds: Duration of the generated video (default: 8s).

        Returns:
            Path to the generated video file, or None if failed.
        """
        import requests

        print(f"[VERTEX-VEO] Generating clip: {video_id}")
        print(f"[VERTEX-VEO] Prompt: {prompt[:100]}...")

        try:
            # Build the endpoint URL for predictLongRunning
            model_id = "veo-2.0-generate-001"
            endpoint_url = (
                f"{self.api_endpoint}/projects/{self.project_id}/locations/{self.location}"
                f"/publishers/google/models/{model_id}:predictLongRunning"
            )

            # Prepare the request payload
            instance = {"prompt": prompt}

            # Add image if provided (for image-to-video)
            if image_path and Path(image_path).exists():
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
                image_b64 = base64.b64encode(image_bytes).decode("utf-8")

                # Determine MIME type from extension
                ext = Path(image_path).suffix.lower()
                mime_types = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".webp": "image/webp",
                    ".gif": "image/gif",
                }
                mime_type = mime_types.get(ext, "image/png")

                instance["image"] = {
                    "bytesBase64Encoded": image_b64,
                    "mimeType": mime_type,
                }
                print(f"[VERTEX-VEO] Using reference image: {image_path} ({mime_type})")

            payload = {
                "instances": [instance],
                "parameters": {
                    "sampleCount": 1,
                    "durationSeconds": min(duration_seconds, 8),
                    "aspectRatio": "16:9",
                }
            }

            # Get access token and make request
            token = self._get_access_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            print(f"[VERTEX-VEO] Calling predictLongRunning endpoint...")
            response = requests.post(endpoint_url, json=payload, headers=headers)

            if response.status_code != 200:
                print(f"[VERTEX-VEO] Error: {response.status_code} - {response.text}")
                return None

            # Get the operation name from response
            operation = response.json()
            operation_name = operation.get("name")

            if not operation_name:
                print(f"[VERTEX-VEO] No operation name in response: {operation}")
                return None

            print(f"[VERTEX-VEO] Operation started: {operation_name}")

            # Poll the operation until complete
            poll_url = f"{self.api_endpoint}/{operation_name}"
            poll_count = 0
            max_polls = 60  # Max 20 minutes (20s * 60)

            while poll_count < max_polls:
                poll_count += 1
                time.sleep(20)

                poll_response = requests.get(poll_url, headers=headers)
                if poll_response.status_code != 200:
                    print(f"[VERTEX-VEO] Poll error: {poll_response.status_code}")
                    continue

                op_status = poll_response.json()
                done = op_status.get("done", False)

                print(f"[VERTEX-VEO] Polling... ({poll_count * 20}s elapsed, done={done})")

                if done:
                    # Check for errors
                    if "error" in op_status:
                        print(f"[VERTEX-VEO] Operation failed: {op_status['error']}")
                        return None

                    # Extract video from response
                    response_data = op_status.get("response", {})
                    generated_samples = response_data.get("generateVideoResponse", {}).get("generatedSamples", [])

                    if not generated_samples:
                        # Try alternative response structure
                        predictions = op_status.get("response", {}).get("predictions", [])
                        if predictions:
                            generated_samples = predictions

                    if generated_samples:
                        # Get the first video
                        sample = generated_samples[0]
                        video_data = sample.get("video", {}).get("bytesBase64Encoded")

                        if not video_data:
                            # Try alternative field names
                            video_data = sample.get("bytesBase64Encoded")

                        if video_data:
                            # Decode and save
                            video_bytes = base64.b64decode(video_data)
                            output_path = Path(output_dir)
                            output_path.mkdir(parents=True, exist_ok=True)
                            video_path = output_path / f"{video_id}.mp4"
                            video_path.write_bytes(video_bytes)
                            print(f"[VERTEX-VEO] Saved: {video_path}")
                            return str(video_path)
                        else:
                            # Check if there's a GCS URI instead
                            gcs_uri = sample.get("video", {}).get("gcsUri")
                            if gcs_uri:
                                print(f"[VERTEX-VEO] Video at GCS: {gcs_uri}")
                                # Download from GCS
                                from google.cloud import storage
                                storage_client = storage.Client()
                                # Parse gs://bucket/path
                                gcs_parts = gcs_uri.replace("gs://", "").split("/", 1)
                                bucket_name = gcs_parts[0]
                                blob_name = gcs_parts[1] if len(gcs_parts) > 1 else ""
                                bucket = storage_client.bucket(bucket_name)
                                blob = bucket.blob(blob_name)

                                output_path = Path(output_dir)
                                output_path.mkdir(parents=True, exist_ok=True)
                                video_path = output_path / f"{video_id}.mp4"
                                blob.download_to_filename(str(video_path))
                                print(f"[VERTEX-VEO] Downloaded from GCS: {video_path}")
                                return str(video_path)

                    print(f"[VERTEX-VEO] No video data in response: {op_status}")
                    return None

            print("[VERTEX-VEO] Operation timed out")
            return None

        except Exception as e:
            import traceback
            print(f"[VERTEX-VEO] Error generating video: {e}")
            traceback.print_exc()
            return None


# ============================================================================
# VEO CLIENT - GEMINI API VERSION (original)
# ============================================================================

class VeoClientGemini:
    """Client for Google Veo video generation via Gemini API."""

    def __init__(self, api_key: str):
        """Initialize the Veo client.

        Args:
            api_key: Google API key for authentication.
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        # Veo 2.0 for better availability
        self.model = "veo-2.0-generate-001"

    def generate_clip(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        output_dir: str = ".",
        video_id: str = "video",
        duration_seconds: int = 8,
    ) -> Optional[str]:
        """Generate a video clip using Veo.

        Args:
            prompt: Text prompt describing the video content.
            image_path: Optional path to an image to use as starting frame.
            output_dir: Directory to save the generated video.
            video_id: Unique identifier for the video file.
            duration_seconds: Duration of the generated video (default: 8s).

        Returns:
            Path to the generated video file, or None if failed.
        """
        print(f"[VEO] Generating clip: {video_id}")
        print(f"[VEO] Prompt: {prompt[:100]}...")

        try:
            # Prepare image if path is provided
            image_obj = None
            if image_path and Path(image_path).exists():
                try:
                    image_obj = types.Image.from_file(location=image_path)
                    print(f"[VEO] Using reference image: {image_path}")
                except Exception as e:
                    print(f"[VEO] Warning: Could not load image: {e}")
                    image_obj = None

            # Create video generation operation
            print(f"[VEO] Starting video generation with model: {self.model}")
            try:
                operation = self.client.models.generate_videos(
                    model=self.model,
                    prompt=prompt,
                    image=image_obj,
                    config=types.GenerateVideosConfig(
                        number_of_videos=1,
                        duration_seconds=duration_seconds,
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
                            duration_seconds=duration_seconds,
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

            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            video_path = output_path / f"{video_id}.mp4"
            video.save(str(video_path))

            print(f"[VEO] Saved: {video_path}")
            return str(video_path)

        except Exception as e:
            print(f"[VEO] Error generating video: {e}")
            return None


# Alias for backwards compatibility
VeoClient = VeoClientGemini


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class GeneratedClip:
    """Represents a generated video clip."""
    clip_id: str
    kf_id: str
    duration: float
    video_path: str
    thumbnail_path: str
    prompt_used: str


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_keyframes(keyframe_plan_path: Path) -> tuple[list, str]:
    """Load keyframes from JSON file."""
    data = json.loads(keyframe_plan_path.read_text(encoding="utf-8"))
    keyframes = data.get("keyframes", [])
    if not isinstance(keyframes, list):
        raise ValueError("keyframe_plan.json 'keyframes' field is not a list")
    title = data.get("title", "Unknown Novel")
    return keyframes, title


def load_trailer_script(trailer_script_path: Path) -> dict:
    """Load trailer script and extract dialogue per beat."""
    if not trailer_script_path.exists():
        print(f"[WARN] trailer_script.json not found at {trailer_script_path}")
        return {}

    data = json.loads(trailer_script_path.read_text(encoding="utf-8"))
    beats = data.get("beats", [])

    # Create mapping: beat_id -> dialogue list
    beat_dialogue = {}
    for beat in beats:
        beat_id = beat.get("beat_id", "")
        dialogue_list = beat.get("dialogue_or_text", [])
        if beat_id and dialogue_list:
            beat_dialogue[beat_id] = dialogue_list

    print(f"[INFO] Loaded dialogue for {len(beat_dialogue)} beats from trailer_script.json")
    return beat_dialogue


def find_keyframe_image(kf_id: str, image_dirs: List[Path]) -> Optional[Path]:
    """Find the image file for a keyframe ID."""
    for img_dir in image_dirs:
        if not img_dir.exists():
            continue
        # Try common extensions
        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
            img_path = img_dir / f"{kf_id}{ext}"
            if img_path.exists():
                return img_path
    return None


def build_video_prompt(kf: dict, global_style: str, dialogue: Optional[List[str]] = None) -> str:
    """Build a prompt for video generation from keyframe data.

    For video generation, we focus on:
    - Action and movement
    - Camera motion
    - Atmosphere and mood
    - Dialogue/text overlays (from trailer_script.json)
    """
    # Get keyframe details
    action = kf.get("action", "")
    shot_type = kf.get("shot_type", "")
    camera_angle = kf.get("camera_angle", "")
    emotion_tags = kf.get("emotion_tags", [])
    image_prompt = kf.get("image_prompt", "")

    # Build a video-focused prompt
    parts = []

    # Style context (shorter for video)
    if global_style:
        # Extract key style elements
        parts.append(f"Visual style: {global_style[:200]}")

    # Shot and camera
    if shot_type:
        parts.append(f"Shot type: {shot_type}")
    if camera_angle:
        parts.append(f"Camera: {camera_angle}")

    # Main action (this is key for video)
    if action:
        parts.append(f"Action: {action}")

    # Mood
    if emotion_tags:
        parts.append(f"Mood: {', '.join(emotion_tags)}")

    # Add dialogue/text from trailer script
    if dialogue:
        for line in dialogue:
            # Check if it's on-screen text or spoken dialogue
            if line.startswith("TEXT:"):
                text_content = line[5:].strip()
                parts.append(f"On-screen text overlay: \"{text_content}\"")
            else:
                parts.append(f"Spoken dialogue: \"{line}\"")

    # Add some of the detailed description
    if image_prompt:
        # Take first 300 chars of image prompt for context
        parts.append(f"Scene details: {image_prompt[:300]}")

    # Video-specific instructions
    parts.append("Cinematic motion, smooth camera movement, atmospheric lighting.")

    return " ".join(parts)


def save_video_generation_output(clips: List[GeneratedClip], output_path: Path, title: str):
    """Save the video generation results to JSON."""
    output = {
        "status": "completed",
        "title": title,
        "generated_clips": [
            {
                "clip_id": clip.clip_id,
                "kf_id": clip.kf_id,
                "duration": clip.duration,
                "video_url": clip.video_path,
                "thumbnail_url": clip.thumbnail_path,
                "prompt_used": clip.prompt_used,
            }
            for clip in clips
        ]
    }
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[INFO] Saved video generation output: {output_path}")


# ============================================================================
# MAIN PIPELINE
# ============================================================================

async def generate_videos_for_keyframes(
    veo_client: VeoClient,
    keyframes: list,
    global_style: str,
    image_dirs: List[Path],
    output_dir: Path,
    beat_dialogue: dict = None,
    duration_seconds: int = 8,
) -> List[GeneratedClip]:
    """Generate videos for all keyframes.

    Note: Veo API calls are synchronous and take time, so we process sequentially
    to avoid rate limits. For production, consider parallel processing with proper
    rate limiting.

    Args:
        veo_client: VeoClient instance for video generation.
        keyframes: List of keyframe dictionaries.
        global_style: Global visual style string.
        image_dirs: List of directories to search for keyframe images.
        output_dir: Directory to save generated videos.
        beat_dialogue: Dict mapping beat_id -> list of dialogue strings.
        duration_seconds: Default duration for video clips.
    """
    generated_clips = []
    total = len(keyframes)
    beat_dialogue = beat_dialogue or {}

    for idx, kf in enumerate(keyframes, 1):
        kf_id = kf.get("kf_id", f"kf_{idx}")
        beat_id = kf.get("beat_id", "")
        duration = kf.get("suggested_duration_sec", duration_seconds)

        # Get dialogue for this beat
        dialogue = beat_dialogue.get(beat_id, [])
        if dialogue:
            print(f"[INFO] Found dialogue for beat {beat_id}: {dialogue[0][:50]}...")

        # Check if video already exists
        video_path = output_dir / f"{kf_id}.mp4"
        if video_path.exists():
            print(f"[{idx}/{total}] Video exists for {kf_id}, skipping...")
            # Still add to results
            image_path = find_keyframe_image(kf_id, image_dirs)
            generated_clips.append(GeneratedClip(
                clip_id=f"clip_{kf_id}",
                kf_id=kf_id,
                duration=duration,
                video_path=str(video_path),
                thumbnail_path=str(image_path) if image_path else "",
                prompt_used="[existing]",
            ))
            continue

        print(f"\n[{idx}/{total}] Processing keyframe: {kf_id}")

        # Find the keyframe image
        image_path = find_keyframe_image(kf_id, image_dirs)
        if image_path:
            print(f"[INFO] Found image: {image_path}")
        else:
            print(f"[WARN] No image found for {kf_id}")

        # Build the prompt (now including dialogue)
        prompt = build_video_prompt(kf, global_style, dialogue)
        print(f"[INFO] Prompt length: {len(prompt)} chars")

        # Generate the video
        # Veo requires duration between 4 and 8 seconds
        clamped_duration = max(4, min(int(duration), 8))
        result_path = veo_client.generate_clip(
            prompt=prompt,
            image_path=str(image_path) if image_path else None,
            output_dir=str(output_dir),
            video_id=kf_id,
            duration_seconds=clamped_duration,
        )

        if result_path:
            generated_clips.append(GeneratedClip(
                clip_id=f"clip_{kf_id}",
                kf_id=kf_id,
                duration=duration,
                video_path=result_path,
                thumbnail_path=str(image_path) if image_path else "",
                prompt_used=prompt,
            ))
            print(f"[SUCCESS] Generated video for {kf_id}")
        else:
            print(f"[FAILED] Could not generate video for {kf_id}")

    return generated_clips


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate videos from keyframe images using Veo")
    parser.add_argument("--use-vertex", action="store_true", help="Use Vertex AI API instead of Gemini API")
    parser.add_argument("--project", type=str, help="Google Cloud project ID (for Vertex AI)")
    parser.add_argument("--location", type=str, default="us-central1", help="Google Cloud location (default: us-central1)")
    args = parser.parse_args()

    load_dotenv()

    # Setup paths
    base_dir = Path(__file__).resolve().parent.parent
    keyframe_plan_path = base_dir / "data" / "keyframe_plan_styled.json"
    world_profile_path = base_dir / "data" / "novel_world_profile.json"
    trailer_script_path = base_dir / "data" / "trailer_script.json"

    # Possible image directories (check _02 first)
    image_dirs = [
    #    base_dir / "output" / "keyframe_images_flux_02",
    #    base_dir / "output" / "keyframe_images00",
        base_dir / "output" / "keyframe_images_03",
    #    base_dir / "output" / "keyframe_images_flux",
    ]

    output_dir = base_dir / "output" / "keyframe_videos_03"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize Veo client based on mode
    if args.use_vertex:
        # Use Vertex AI
        project_id = args.project or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            raise ValueError("Google Cloud project ID required. Use --project or set GOOGLE_CLOUD_PROJECT env var")
        print(f"[INFO] Using Vertex AI with project: {project_id}")
        veo_client = VeoClientVertex(project_id=project_id, location=args.location)
    else:
        # Use Gemini API
        api_key = os.getenv("GOOGLE_API_KEY_2") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        print(f"[INFO] Using Gemini API with key: {api_key[:10]}...")
        veo_client = VeoClientGemini(api_key=api_key)

    # Load world profile for global style
    global_style = ""
    if world_profile_path.exists():
        world_profile = json.loads(world_profile_path.read_text(encoding="utf-8"))
        global_style = world_profile.get("global_style", "")
        print(f"[INFO] Loaded global style from world profile")

    # Load dialogue from trailer script
    beat_dialogue = load_trailer_script(trailer_script_path)

    # Load keyframes
    keyframes, title = load_keyframes(keyframe_plan_path)
    print(f"[INFO] Novel: {title}")
    print(f"[INFO] Loaded {len(keyframes)} keyframes")

    # Check which image directory has images
    for img_dir in image_dirs:
        if img_dir.exists():
            count = len(list(img_dir.glob("*.png"))) + len(list(img_dir.glob("*.jpg")))
            print(f"[INFO] Found {count} images in {img_dir}")

    # Generate videos
    print("\n" + "="*60)
    print("STARTING VIDEO GENERATION")
    print("="*60)

    generated_clips = asyncio.run(
        generate_videos_for_keyframes(
            veo_client=veo_client,
            keyframes=keyframes,
            global_style=global_style,
            image_dirs=image_dirs,
            output_dir=output_dir,
            beat_dialogue=beat_dialogue,
            duration_seconds=8,
        )
    )

    # Save output
    output_json_path = base_dir / "output" / "video_generation.json"
    save_video_generation_output(generated_clips, output_json_path, title)

    # Summary
    print("\n" + "="*60)
    print("VIDEO GENERATION SUMMARY")
    print("="*60)
    print(f"Total keyframes:      {len(keyframes)}")
    print(f"Videos generated:     {len(generated_clips)}")
    print(f"Output directory:     {output_dir}")
    print(f"Output JSON:          {output_json_path}")
    print("="*60)


if __name__ == "__main__":
    main()
