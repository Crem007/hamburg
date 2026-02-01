"""
Generator Backend API

FastAPI backend for the Generator text-to-visual-narrative application.
Endpoints:
- POST /api/extract-scenes - Extract key visual scenes from text using Gemini
- POST /api/generate - Generate images for scenes using Gemini
- POST /api/regenerate - Regenerate a single image using Gemini
- POST /api/demo-generate - Full pipeline for single scene (image -> layers -> video)
- GET /api/book - Fetch book text from Project Gutenberg
- POST /api/research/start - Start a new Manus research task
- GET /api/research/status/{task_id} - Check task status
- GET /api/research/reports - List all completed reports
- GET /api/research/reports/{report_id} - Get specific report details
"""

import os
import time
import asyncio
import httpx
import base64
import json
from typing import Optional, List
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types
import fal_client
from PIL import Image
import io

# Load environment variables
load_dotenv()

# Gemini image generation model
GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"

# Style presets with their prompt modifiers
STYLE_PRESETS = {
    "cinematic": "Cinematic photography style, dramatic lighting, film grain, shallow depth of field, professional color grading",
    "anime": "Anime art style, vibrant colors, clean lines, expressive characters, studio quality animation cel",
    "oil_painting": "Classical oil painting style, visible brushstrokes, rich textures, Renaissance-inspired composition, museum quality",
    "photorealistic": "Photorealistic, hyperrealistic detail, 8K resolution, professional photography, natural lighting",
    "watercolor": "Watercolor painting style, soft edges, flowing colors, delicate washes, artistic paper texture",
    "noir": "Film noir style, high contrast black and white, dramatic shadows, 1940s aesthetic, moody atmosphere",
}

# Global Gemini client
gemini_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources."""
    global gemini_client

    # Initialize Gemini
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if api_key:
        gemini_client = genai.Client(api_key=api_key)
        print("[INFO] Gemini client initialized")

    yield

    print("[INFO] Shutting down API")


app = FastAPI(
    title="Generator API",
    description="Turn any text into visual narrative",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class ExtractScenesRequest(BaseModel):
    text: str
    num_scenes: int = 4


class Scene(BaseModel):
    id: int
    description: str
    prompt: str


class ExtractScenesResponse(BaseModel):
    scenes: List[Scene]


class GenerateRequest(BaseModel):
    scenes: List[Scene]
    style: str = "cinematic"
    character: str = "none"


class GeneratedImage(BaseModel):
    id: int
    url: str
    prompt: str


class GenerateResponse(BaseModel):
    images: List[GeneratedImage]
    generation_time_seconds: float


class RegenerateRequest(BaseModel):
    prompt: str
    style: str = "cinematic"
    character: str = "none"


class RegenerateResponse(BaseModel):
    url: str
    generation_time_seconds: float


class BookResponse(BaseModel):
    title: str
    author: str
    text: str


# Demo generation models
class DemoGenerateRequest(BaseModel):
    text: str
    scene_number: int = 1


class DemoScene(BaseModel):
    id: int
    description: str
    prompt: str
    action: str


class DemoLayer(BaseModel):
    index: int
    url: str


class DemoGenerateResponse(BaseModel):
    status: str  # extracting_scene, generating_image, extracting_layers, generating_video, complete
    scene: Optional[DemoScene] = None
    image_url: Optional[str] = None
    layers: Optional[List[DemoLayer]] = None
    video_url: Optional[str] = None
    total_time_seconds: Optional[float] = None
    error: Optional[str] = None


# ============================================================================
# Market Research Models
# ============================================================================

class ResearchRequest(BaseModel):
    topic: str = "web_novel_trends"
    genres: List[str] = []  # Optional: focus on specific genres
    platforms: List[str] = []  # Optional: specific platforms


class ResearchTask(BaseModel):
    task_id: str
    status: str  # pending, running, completed, failed
    created_at: datetime
    progress: Optional[int] = None


class GenreInsight(BaseModel):
    name: str
    popularity_score: float
    growth_trend: str  # rising, stable, declining
    key_themes: List[str]
    visual_style: str
    description: str = ""


class NovelRecommendation(BaseModel):
    title: str
    author: str
    genre: str
    platform: str
    rating: float
    synopsis: str
    trailer_potential: str  # high, medium, low
    visual_hooks: List[str]


class TrailerIdea(BaseModel):
    title: str
    description: str
    visual_elements: List[str]
    target_emotion: str
    suggested_music_style: str


class ResearchReport(BaseModel):
    id: str
    title: str
    summary: str
    created_at: str
    genres: List[GenreInsight]
    trending_novels: List[NovelRecommendation]
    trailer_suggestions: List[TrailerIdea]
    platforms_analyzed: List[str]


class ResearchReportList(BaseModel):
    reports: List[ResearchReport]


# ============================================================================
# Helper Functions for Demo Pipeline
# ============================================================================

def image_to_data_uri(image_bytes: bytes) -> str:
    """Convert image bytes to data URI"""
    image_data = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{image_data}"


def generate_image_with_gemini(
    client,
    prompt: str,
    aspect_ratio: str = "1:1"
) -> Optional[bytes]:
    """Generate image using Gemini and return bytes."""
    try:
        response = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                )
            ),
        )

        if response.parts:
            for part in response.parts:
                if part.inline_data is not None:
                    img = part.as_image()  # PIL Image
                    # Convert PIL Image to bytes
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format="PNG")
                    return img_buffer.getvalue()
        return None
    except Exception as e:
        print(f"[ERROR] Gemini image generation failed: {e}")
        return None


async def download_image_bytes(url: str) -> Optional[bytes]:
    """Download image from URL and return bytes"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()
            return response.content
    except Exception as e:
        print(f"[ERROR] Failed to download image: {e}")
        return None


def decompose_image_layers_sync(image_bytes: bytes, num_layers: int = 4) -> Optional[List[dict]]:
    """Decompose image into layers using fal.ai Qwen"""
    try:
        image_uri = image_to_data_uri(image_bytes)
        result = fal_client.subscribe(
            "fal-ai/qwen-image-layered",
            arguments={
                "image_url": image_uri,
                "num_layers": num_layers,
            },
            with_logs=True,
        )
        if result and "layers" in result:
            return [
                {"url": layer.get("url"), "index": i}
                for i, layer in enumerate(result["layers"])
                if layer.get("url")
            ]
        elif result and "images" in result:
            return [
                {"url": img.get("url"), "index": i}
                for i, img in enumerate(result["images"])
                if img.get("url")
            ]
        return None
    except Exception as e:
        print(f"[ERROR] Layer decomposition failed: {e}")
        return None


def generate_video_veo(
    prompt: str,
    image_bytes: Optional[bytes] = None,
    duration_seconds: int = 8
) -> Optional[str]:
    """Generate video using Veo API. Returns video URL or None."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] No Google API key for Veo")
        return None

    try:
        client = genai.Client(api_key=api_key)
        model = "veo-2.0-generate-001"  # Use faster model for demo

        # Prepare image if provided
        image_obj = None
        if image_bytes:
            try:
                # Save temporarily and load
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                    f.write(image_bytes)
                    temp_path = f.name
                image_obj = types.Image.from_file(location=temp_path)
                Path(temp_path).unlink(missing_ok=True)
            except Exception as e:
                print(f"[WARN] Could not use image for Veo: {e}")
                image_obj = None

        print(f"[VEO] Generating video with prompt: {prompt[:100]}...")
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            image=image_obj,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=duration_seconds,
            ),
        )

        # Poll until completion
        poll_count = 0
        while not operation.done:
            poll_count += 1
            print(f"[VEO] Polling... ({poll_count * 10}s)")
            time.sleep(10)
            operation = client.operations.get(operation)

        # Get video URL
        video = operation.response.generated_videos[0].video
        client.files.download(file=video)

        # Save to temp and return path (or we could return base64)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            video.save(f.name)
            return f.name

    except Exception as e:
        print(f"[ERROR] Veo generation failed: {e}")
        return None


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    return {"message": "Generator API", "status": "running"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "gemini": gemini_client is not None,
    }


@app.get("/api/research/markdown")
async def get_research_markdown():
    """Get the pre-generated research markdown file."""
    markdown_path = Path(__file__).parent.parent / "data" / "Web_Novel_Market_Research_ 2026 Trends.md"
    
    if not markdown_path.exists():
        raise HTTPException(status_code=404, detail="Research report not found")
    
    content = markdown_path.read_text(encoding="utf-8")
    return {"content": content, "filename": markdown_path.name}


@app.post("/api/extract-scenes", response_model=ExtractScenesResponse)
async def extract_scenes(request: ExtractScenesRequest):
    """Extract key visual scenes from text using Gemini."""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini client not initialized")

    if len(request.text) < 50:
        raise HTTPException(status_code=400, detail="Text too short. Please provide at least 50 characters.")

    # Truncate very long text
    text = request.text[:15000] if len(request.text) > 15000 else request.text

    prompt = f"""Analyze the following text and extract exactly {request.num_scenes} key visual scenes that would make compelling images.

For each scene, provide:
1. A brief description (1-2 sentences) of what's happening
2. A detailed image generation prompt (describe visual elements, composition, lighting, mood, colors, style)

Text to analyze:
---
{text}
---

Respond in this exact JSON format:
{{
  "scenes": [
    {{
      "id": 1,
      "description": "Brief description of the scene",
      "prompt": "Detailed image prompt with visual elements, composition, lighting, mood, colors"
    }},
    ...
  ]
}}

Focus on the most visually striking and narratively important moments. Make the prompts detailed and specific for image generation."""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        # Parse JSON from response
        response_text = response.text

        # Extract JSON from markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        import json
        data = json.loads(response_text.strip())

        scenes = [
            Scene(id=s["id"], description=s["description"], prompt=s["prompt"])
            for s in data["scenes"]
        ]

        return ExtractScenesResponse(scenes=scenes)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scene extraction failed: {str(e)}")


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_images(request: GenerateRequest):
    """Generate images for scenes using Gemini."""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini client not initialized")

    style_modifier = STYLE_PRESETS.get(request.style, STYLE_PRESETS["cinematic"])

    # Add character to prompts if specified
    character_modifier = ""
    if request.character and request.character != "none":
        character_modifier = f", featuring {request.character}"

    start_time = time.time()
    images = []

    # Generate images sequentially (Gemini doesn't support concurrent image gen well)
    for scene in request.scenes:
        full_prompt = f"{style_modifier}. {scene.prompt}{character_modifier}"

        try:
            loop = asyncio.get_event_loop()
            image_bytes = await loop.run_in_executor(
                None, generate_image_with_gemini, gemini_client, full_prompt, "1:1"
            )

            if image_bytes:
                image_url = image_to_data_uri(image_bytes)
                images.append(GeneratedImage(
                    id=scene.id,
                    url=image_url,
                    prompt=full_prompt,
                ))
        except Exception as e:
            print(f"[ERROR] Failed to generate image for scene {scene.id}: {e}")

    generation_time = time.time() - start_time

    return GenerateResponse(
        images=images,
        generation_time_seconds=round(generation_time, 2),
    )


@app.post("/api/regenerate", response_model=RegenerateResponse)
async def regenerate_image(request: RegenerateRequest):
    """Regenerate a single image with optional prompt tweaks."""
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini client not initialized")

    style_modifier = STYLE_PRESETS.get(request.style, STYLE_PRESETS["cinematic"])

    character_modifier = ""
    if request.character and request.character != "none":
        character_modifier = f", featuring {request.character}"

    full_prompt = f"{style_modifier}. {request.prompt}{character_modifier}"

    start_time = time.time()

    try:
        loop = asyncio.get_event_loop()
        image_bytes = await loop.run_in_executor(
            None, generate_image_with_gemini, gemini_client, full_prompt, "1:1"
        )

        if image_bytes:
            generation_time = time.time() - start_time
            return RegenerateResponse(
                url=image_to_data_uri(image_bytes),
                generation_time_seconds=round(generation_time, 2),
            )

        raise HTTPException(status_code=500, detail="No image returned from Gemini")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image regeneration failed: {str(e)}")


@app.get("/api/book", response_model=BookResponse)
async def fetch_book(title: str = Query(..., description="Book title to search for")):
    """Fetch book text from Project Gutenberg via Gutendex API."""

    async with httpx.AsyncClient() as client:
        # Search for book
        search_url = f"https://gutendex.com/books?search={title}"

        try:
            response = await client.get(search_url, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            if not data.get("results"):
                raise HTTPException(status_code=404, detail=f"Book not found: {title}")

            book = data["results"][0]
            book_title = book.get("title", title)
            authors = book.get("authors", [])
            author = authors[0].get("name", "Unknown") if authors else "Unknown"

            # Get text format URL
            formats = book.get("formats", {})
            text_url = (
                formats.get("text/plain; charset=utf-8") or
                formats.get("text/plain; charset=us-ascii") or
                formats.get("text/plain")
            )

            if not text_url:
                raise HTTPException(status_code=404, detail="No plain text format available for this book")

            # Fetch book text
            text_response = await client.get(text_url, timeout=60.0)
            text_response.raise_for_status()
            text = text_response.text

            # Truncate to reasonable size (first ~10000 chars after header)
            # Skip Gutenberg header (usually first 500-1000 chars)
            start_marker = "*** START OF"
            if start_marker in text:
                text = text.split(start_marker)[1]
                # Skip the rest of the header line
                text = text.split("\n", 1)[1] if "\n" in text else text

            # Truncate
            text = text[:10000].strip()

            return BookResponse(
                title=book_title,
                author=author,
                text=text,
            )

        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Failed to fetch book: {str(e)}")


@app.post("/api/demo-generate")
async def demo_generate(request: DemoGenerateRequest):
    """
    Full demo pipeline: text -> scene -> image -> layers -> video
    Returns progress updates as streaming JSON.
    """
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini client not initialized")

    async def generate_stream():
        start_time = time.time()
        scene = None
        image_url = None
        image_bytes = None
        layers = None
        video_path = None

        try:
            # Step 1: Extract scene
            yield json.dumps({"status": "extracting_scene"}) + "\n"

            extract_prompt = f"""Analyze this text and extract ONE key visual scene for a cinematic trailer.

Text:
---
{request.text[:5000]}
---

Return JSON:
{{
  "id": {request.scene_number},
  "description": "Brief 1-2 sentence description",
  "prompt": "Detailed image prompt with visual elements, composition, lighting, mood",
  "action": "Brief description of movement/action for video generation"
}}"""

            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=extract_prompt,
            )
            response_text = response.text
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            scene_data = json.loads(response_text.strip())
            scene = DemoScene(**scene_data)

            yield json.dumps({
                "status": "generating_image",
                "scene": scene.model_dump()
            }) + "\n"

            # Step 2: Generate image using Gemini
            style = STYLE_PRESETS["cinematic"]
            full_prompt = f"{style}. {scene.prompt}"

            loop = asyncio.get_event_loop()
            image_bytes = await loop.run_in_executor(
                None, generate_image_with_gemini, gemini_client, full_prompt, "9:16"
            )

            if image_bytes:
                image_url = image_to_data_uri(image_bytes)

            yield json.dumps({
                "status": "extracting_layers",
                "scene": scene.model_dump(),
                "image_url": image_url
            }) + "\n"

            # Step 3: Extract layers
            if image_bytes:
                # Run in thread pool since fal_client is sync
                loop = asyncio.get_event_loop()
                layer_results = await loop.run_in_executor(
                    None, decompose_image_layers_sync, image_bytes, 4
                )
                if layer_results:
                    layers = [DemoLayer(index=l["index"], url=l["url"]) for l in layer_results]

            yield json.dumps({
                "status": "generating_video",
                "scene": scene.model_dump(),
                "image_url": image_url,
                "layers": [l.model_dump() for l in layers] if layers else None
            }) + "\n"

            # Step 4: Generate video
            video_prompt = f"Cinematic motion, smooth camera movement. {scene.action}. {scene.prompt[:300]}"
            loop = asyncio.get_event_loop()
            video_path = await loop.run_in_executor(
                None, generate_video_veo, video_prompt, image_bytes, 8
            )

            # Convert video to base64 data URL for response
            video_url = None
            if video_path and Path(video_path).exists():
                video_bytes = Path(video_path).read_bytes()
                video_base64 = base64.b64encode(video_bytes).decode("utf-8")
                video_url = f"data:video/mp4;base64,{video_base64}"
                Path(video_path).unlink(missing_ok=True)

            total_time = time.time() - start_time

            yield json.dumps({
                "status": "complete",
                "scene": scene.model_dump(),
                "image_url": image_url,
                "layers": [l.model_dump() for l in layers] if layers else None,
                "video_url": video_url,
                "total_time_seconds": round(total_time, 2)
            }) + "\n"

        except Exception as e:
            print(f"[ERROR] Demo generation failed: {e}")
            yield json.dumps({
                "status": "error",
                "error": str(e)
            }) + "\n"

    return StreamingResponse(
        generate_stream(),
        media_type="application/x-ndjson"
    )


# ============================================================================
# Market Research Endpoints
# ============================================================================

# Manus API configuration
MANUS_BASE_URL = "https://api.manus.ai/v1"
MANUS_API_KEY = os.getenv("MANUS_API_KEY")

# Research output directory
RESEARCH_OUTPUT_DIR = Path(__file__).parent.parent / "output" / "market_research"
RESEARCH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# In-memory task tracking (in production, use Redis or database)
research_tasks: dict = {}


RESEARCH_PROMPT_TEMPLATE = """
Conduct comprehensive market research on current web novel trends across major platforms.

Platforms to analyze:
{platforms}

Research objectives:
1. Identify trending genres and subgenres with growth metrics
2. Find top-performing novels and their key characteristics
3. Analyze reader demographics and preferences per platform
4. Identify trailer-worthy novels with strong visual appeal
5. Extract common storytelling hooks and marketing angles

{genre_focus}

Please provide your findings in a structured format with:

## Genre Rankings
For each major genre, provide:
- Genre name
- Popularity score (0-100)
- Growth trend (rising/stable/declining)
- Key themes and tropes
- Recommended visual style for trailers

## Trending Novels
For each recommended novel:
- Title and author
- Genre and platform
- Rating/popularity metrics
- Brief synopsis
- Trailer potential (high/medium/low)
- Visual hooks (specific scenes or elements that would work well in a trailer)

## Trailer Ideas
Provide creative trailer concepts including:
- Title/theme
- Description of the concept
- Key visual elements
- Target emotional response
- Suggested music style

Focus on novels that would translate well to visual trailers.
"""

DEFAULT_PLATFORMS = [
    "Webnovel (Qidian International)",
    "Royal Road",
    "Wattpad",
    "Tapas",
    "Kindle Unlimited / KDP",
    "Scribble Hub",
]


@app.post("/api/research/start", response_model=ResearchTask)
async def start_research(request: ResearchRequest):
    """Start a new Manus research task for web novel market research."""
    if not MANUS_API_KEY:
        raise HTTPException(status_code=503, detail="Manus API key not configured")

    platforms_list = request.platforms if request.platforms else DEFAULT_PLATFORMS
    platforms_str = "\n".join(f"- {p}" for p in platforms_list)

    genre_focus = ""
    if request.genres:
        genre_focus = f"\nFocus particularly on these genres: {', '.join(request.genres)}\n"

    prompt = RESEARCH_PROMPT_TEMPLATE.format(
        platforms=platforms_str,
        genre_focus=genre_focus,
    )

    headers = {
        "API_KEY": MANUS_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "agentProfile": "manus-1.6",
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{MANUS_BASE_URL}/tasks",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        task_id = data.get("id") or data.get("task_id")
        if not task_id:
            raise HTTPException(status_code=500, detail="No task ID returned from Manus")

        # Track the task
        task = ResearchTask(
            task_id=task_id,
            status="pending",
            created_at=datetime.now(),
        )
        research_tasks[task_id] = {
            "task": task,
            "request": request,
        }

        return task

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Manus API error: {str(e)}")


@app.get("/api/research/status/{task_id}", response_model=ResearchTask)
async def get_research_status(task_id: str):
    """Check the status of a Manus research task."""
    if not MANUS_API_KEY:
        raise HTTPException(status_code=503, detail="Manus API key not configured")

    headers = {
        "API_KEY": MANUS_API_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{MANUS_BASE_URL}/tasks/{task_id}",
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        status = data.get("status", "unknown")
        progress = data.get("progress")

        # Map Manus status to our status
        status_map = {
            "pending": "pending",
            "running": "running",
            "in_progress": "running",
            "completed": "completed",
            "complete": "completed",
            "done": "completed",
            "failed": "failed",
            "error": "failed",
        }
        normalized_status = status_map.get(status.lower(), status)

        # If completed, try to save the report
        if normalized_status == "completed":
            await _save_research_result(task_id, data)

        return ResearchTask(
            task_id=task_id,
            status=normalized_status,
            created_at=research_tasks.get(task_id, {}).get("task", {}).created_at if task_id in research_tasks else datetime.now(),
            progress=progress,
        )

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Manus API error: {str(e)}")


async def _save_research_result(task_id: str, data: dict):
    """Save research result to JSON file."""
    raw_content = ""

    # Try to get content from result
    if "result" in data:
        raw_content = data["result"]
    elif "output" in data:
        raw_content = data["output"]
    elif "content" in data:
        raw_content = data["content"]

    if not raw_content:
        return

    # Parse into structured report
    report = _parse_research_content(raw_content, task_id)

    # Save to file
    filename = f"report_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = RESEARCH_OUTPUT_DIR / filename

    with open(filepath, "w") as f:
        json.dump(report, f, indent=2)


def _parse_research_content(raw_content: str, task_id: str) -> dict:
    """Parse raw Manus output into structured report dict."""
    report = {
        "id": task_id,
        "title": "Web Novel Market Research",
        "summary": "",
        "created_at": datetime.now().isoformat(),
        "genres": [],
        "trending_novels": [],
        "trailer_suggestions": [],
        "platforms_analyzed": DEFAULT_PLATFORMS,
    }

    if not raw_content:
        report["summary"] = "No content received"
        return report

    # Simple parsing - extract sections
    lines = raw_content.split("\n")
    current_section = None

    genres = []
    novels = []
    trailers = []

    for line in lines:
        line_lower = line.lower().strip()

        if "genre ranking" in line_lower or "genre insight" in line_lower:
            current_section = "genres"
            continue
        elif "trending novel" in line_lower or "recommended novel" in line_lower:
            current_section = "novels"
            continue
        elif "trailer idea" in line_lower or "trailer concept" in line_lower:
            current_section = "trailers"
            continue
        elif line.startswith("## "):
            current_section = None

        if current_section == "genres" and line.strip():
            if line.startswith("- ") or line.startswith("* "):
                genre_name = line[2:].split(":")[0].strip()
                if genre_name and len(genre_name) < 50:
                    genres.append({
                        "name": genre_name,
                        "popularity_score": 75.0,
                        "growth_trend": "rising",
                        "key_themes": [],
                        "visual_style": "cinematic",
                        "description": "",
                    })

        elif current_section == "novels" and line.strip():
            if line.startswith("- ") or line.startswith("* ") or line.startswith("###"):
                title = line.lstrip("-* #").split(":")[0].strip()
                if title and len(title) < 100:
                    novels.append({
                        "title": title,
                        "author": "Unknown",
                        "genre": "Fantasy",
                        "platform": "Webnovel",
                        "rating": 4.5,
                        "synopsis": "",
                        "trailer_potential": "high",
                        "visual_hooks": [],
                    })

        elif current_section == "trailers" and line.strip():
            if line.startswith("- ") or line.startswith("* ") or line.startswith("###"):
                title = line.lstrip("-* #").split(":")[0].strip()
                if title and len(title) < 100:
                    trailers.append({
                        "title": title,
                        "description": "",
                        "visual_elements": [],
                        "target_emotion": "excitement",
                        "suggested_music_style": "epic orchestral",
                    })

    summary_parts = []
    if genres:
        summary_parts.append(f"Identified {len(genres)} trending genres")
    if novels:
        summary_parts.append(f"Found {len(novels)} recommended novels")
    if trailers:
        summary_parts.append(f"Generated {len(trailers)} trailer ideas")

    report["summary"] = ". ".join(summary_parts) if summary_parts else "Research complete"
    report["genres"] = genres[:10]
    report["trending_novels"] = novels[:20]
    report["trailer_suggestions"] = trailers[:10]

    return report


@app.get("/api/research/reports", response_model=ResearchReportList)
async def list_research_reports():
    """List all completed research reports."""
    reports = []

    for filepath in RESEARCH_OUTPUT_DIR.glob("report_*.json"):
        try:
            with open(filepath) as f:
                report_data = json.load(f)
                reports.append(ResearchReport(**report_data))
        except Exception as e:
            print(f"[WARN] Failed to load {filepath}: {e}")

    # Sort by created_at descending
    reports.sort(key=lambda r: r.created_at, reverse=True)

    return ResearchReportList(reports=reports)


@app.get("/api/research/reports/{report_id}", response_model=ResearchReport)
async def get_research_report(report_id: str):
    """Get a specific research report by ID."""
    for filepath in RESEARCH_OUTPUT_DIR.glob(f"report_{report_id}_*.json"):
        try:
            with open(filepath) as f:
                report_data = json.load(f)
                return ResearchReport(**report_data)
        except Exception as e:
            print(f"[WARN] Failed to load {filepath}: {e}")

    raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
