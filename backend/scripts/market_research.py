"""
Market Research Script using Manus AI

Standalone script to conduct web novel market research using the Manus API.
Submits research tasks, polls for completion, and structures the results.

Usage:
    python market_research.py --test  # Test with a simple task
    python market_research.py         # Run full market research
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, asdict

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Manus API configuration
MANUS_BASE_URL = "https://api.manus.ai/v1"
MANUS_API_KEY = os.getenv("MANUS_API_KEY")

# Output directory for cached reports
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "market_research"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# Data Classes for Structured Output
# ============================================================================

@dataclass
class GenreInsight:
    name: str
    popularity_score: float
    growth_trend: str  # rising, stable, declining
    key_themes: List[str]
    visual_style: str
    description: str = ""


@dataclass
class NovelRecommendation:
    title: str
    author: str
    genre: str
    platform: str
    rating: float
    synopsis: str
    trailer_potential: str  # high, medium, low
    visual_hooks: List[str]


@dataclass
class TrailerIdea:
    title: str
    description: str
    visual_elements: List[str]
    target_emotion: str
    suggested_music_style: str


@dataclass
class ResearchReport:
    id: str
    title: str
    summary: str
    created_at: str
    genres: List[GenreInsight]
    trending_novels: List[NovelRecommendation]
    trailer_suggestions: List[TrailerIdea]
    platforms_analyzed: List[str]
    raw_content: str = ""


# ============================================================================
# Research Task Prompt
# ============================================================================

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

## Platform Insights
Brief analysis of each platform's unique characteristics and audience.

Focus on novels that would translate well to visual trailers - prioritize stories with:
- Strong visual imagery
- Dramatic moments
- Clear emotional arcs
- Memorable characters
- Epic or intimate scenes that can be captured in short clips
"""

DEFAULT_PLATFORMS = [
    "Webnovel (Qidian International)",
    "Royal Road",
    "Wattpad",
    "Tapas",
    "Kindle Unlimited / KDP",
    "Scribble Hub",
]


# ============================================================================
# Manus API Functions
# ============================================================================

def create_research_task(
    topic: str = "web_novel_trends",
    genres: Optional[List[str]] = None,
    platforms: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Submit a research task to Manus API.
    Returns the task ID if successful, None otherwise.
    """
    if not MANUS_API_KEY:
        print("[ERROR] MANUS_API_KEY not found in environment variables")
        return None

    platforms_list = platforms or DEFAULT_PLATFORMS
    platforms_str = "\n".join(f"- {p}" for p in platforms_list)

    genre_focus = ""
    if genres:
        genre_focus = f"\nFocus particularly on these genres: {', '.join(genres)}\n"

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
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{MANUS_BASE_URL}/tasks",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            task_id = data.get("id") or data.get("task_id")
            print(f"[INFO] Created Manus task: {task_id}")
            return task_id
    except httpx.HTTPError as e:
        print(f"[ERROR] Failed to create Manus task: {e}")
        return None


def get_task_status(task_id: str) -> dict:
    """
    Poll Manus API for task status.
    Returns dict with status, progress, and result if complete.
    """
    if not MANUS_API_KEY:
        return {"status": "error", "error": "No API key"}

    headers = {
        "API_KEY": MANUS_API_KEY,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.get(
                f"{MANUS_BASE_URL}/tasks/{task_id}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        print(f"[ERROR] Failed to get task status: {e}")
        return {"status": "error", "error": str(e)}


def download_file(file_id: str) -> Optional[str]:
    """
    Download a file from Manus API.
    Returns the file content as string.
    """
    if not MANUS_API_KEY:
        return None

    headers = {
        "API_KEY": MANUS_API_KEY,
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.get(
                f"{MANUS_BASE_URL}/files/{file_id}",
                headers=headers,
            )
            response.raise_for_status()
            return response.text
    except httpx.HTTPError as e:
        print(f"[ERROR] Failed to download file: {e}")
        return None


def poll_until_complete(
    task_id: str,
    poll_interval: int = 10,
    max_polls: int = 120,
) -> dict:
    """
    Poll task status until completion or timeout.
    Returns the final task status.
    """
    print(f"[INFO] Polling task {task_id}...")

    for i in range(max_polls):
        status = get_task_status(task_id)
        task_status = status.get("status", "unknown")

        print(f"[INFO] Poll {i + 1}/{max_polls}: status={task_status}")

        if task_status in ("completed", "complete", "done"):
            print("[INFO] Task completed!")
            return status
        elif task_status in ("failed", "error"):
            print(f"[ERROR] Task failed: {status.get('error', 'Unknown error')}")
            return status

        time.sleep(poll_interval)

    print("[ERROR] Task timed out")
    return {"status": "timeout", "error": "Polling timed out"}


# ============================================================================
# Report Parsing
# ============================================================================

def parse_research_report(raw_content: str, task_id: str) -> ResearchReport:
    """
    Parse raw Manus output into structured ResearchReport.
    """
    # Default empty report
    report = ResearchReport(
        id=task_id,
        title="Web Novel Market Research",
        summary="",
        created_at=datetime.now().isoformat(),
        genres=[],
        trending_novels=[],
        trailer_suggestions=[],
        platforms_analyzed=DEFAULT_PLATFORMS,
        raw_content=raw_content,
    )

    if not raw_content:
        report.summary = "No content received from research task"
        return report

    # Try to extract sections from the content
    lines = raw_content.split("\n")
    current_section = None
    section_content = []

    genres = []
    novels = []
    trailers = []

    for line in lines:
        line_lower = line.lower().strip()

        # Detect section headers
        if "genre ranking" in line_lower or "genre insight" in line_lower:
            current_section = "genres"
            continue
        elif "trending novel" in line_lower or "recommended novel" in line_lower:
            current_section = "novels"
            continue
        elif "trailer idea" in line_lower or "trailer concept" in line_lower:
            current_section = "trailers"
            continue
        elif "platform insight" in line_lower or "platform analysis" in line_lower:
            current_section = "platforms"
            continue
        elif line.startswith("## "):
            current_section = None

        # Parse content based on section
        if current_section == "genres" and line.strip():
            # Simple heuristic parsing for genres
            if line.startswith("- ") or line.startswith("* "):
                genre_name = line[2:].split(":")[0].strip()
                if genre_name and len(genre_name) < 50:
                    genres.append(GenreInsight(
                        name=genre_name,
                        popularity_score=75.0,  # Default
                        growth_trend="rising",
                        key_themes=[],
                        visual_style="cinematic",
                    ))

        elif current_section == "novels" and line.strip():
            # Simple heuristic parsing for novels
            if line.startswith("- ") or line.startswith("* ") or line.startswith("###"):
                title = line.lstrip("-* #").split(":")[0].strip()
                if title and len(title) < 100:
                    novels.append(NovelRecommendation(
                        title=title,
                        author="Unknown",
                        genre="Fantasy",
                        platform="Webnovel",
                        rating=4.5,
                        synopsis="",
                        trailer_potential="high",
                        visual_hooks=[],
                    ))

        elif current_section == "trailers" and line.strip():
            if line.startswith("- ") or line.startswith("* ") or line.startswith("###"):
                title = line.lstrip("-* #").split(":")[0].strip()
                if title and len(title) < 100:
                    trailers.append(TrailerIdea(
                        title=title,
                        description="",
                        visual_elements=[],
                        target_emotion="excitement",
                        suggested_music_style="epic orchestral",
                    ))

    # Generate summary
    summary_parts = []
    if genres:
        summary_parts.append(f"Identified {len(genres)} trending genres")
    if novels:
        summary_parts.append(f"Found {len(novels)} recommended novels")
    if trailers:
        summary_parts.append(f"Generated {len(trailers)} trailer ideas")

    report.summary = ". ".join(summary_parts) if summary_parts else "Research complete"
    report.genres = genres[:10]  # Limit to top 10
    report.trending_novels = novels[:20]  # Limit to top 20
    report.trailer_suggestions = trailers[:10]

    return report


# ============================================================================
# Cache Management
# ============================================================================

def save_report(report: ResearchReport) -> Path:
    """Save report to JSON file."""
    filename = f"report_{report.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = OUTPUT_DIR / filename

    # Convert to dict for JSON serialization
    report_dict = {
        "id": report.id,
        "title": report.title,
        "summary": report.summary,
        "created_at": report.created_at,
        "genres": [asdict(g) for g in report.genres],
        "trending_novels": [asdict(n) for n in report.trending_novels],
        "trailer_suggestions": [asdict(t) for t in report.trailer_suggestions],
        "platforms_analyzed": report.platforms_analyzed,
        "raw_content": report.raw_content,
    }

    with open(filepath, "w") as f:
        json.dump(report_dict, f, indent=2)

    print(f"[INFO] Saved report to {filepath}")
    return filepath


def load_reports() -> List[dict]:
    """Load all cached reports."""
    reports = []
    for filepath in OUTPUT_DIR.glob("report_*.json"):
        try:
            with open(filepath) as f:
                reports.append(json.load(f))
        except Exception as e:
            print(f"[WARN] Failed to load {filepath}: {e}")
    return sorted(reports, key=lambda r: r.get("created_at", ""), reverse=True)


def load_report(report_id: str) -> Optional[dict]:
    """Load a specific report by ID."""
    for filepath in OUTPUT_DIR.glob(f"report_{report_id}_*.json"):
        try:
            with open(filepath) as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load {filepath}: {e}")
    return None


# ============================================================================
# Main Functions
# ============================================================================

def run_research(
    topic: str = "web_novel_trends",
    genres: Optional[List[str]] = None,
    platforms: Optional[List[str]] = None,
) -> Optional[ResearchReport]:
    """
    Run full research workflow: create task, poll, parse, save.
    """
    print(f"[INFO] Starting market research: {topic}")

    # Create task
    task_id = create_research_task(topic, genres, platforms)
    if not task_id:
        return None

    # Poll until complete
    result = poll_until_complete(task_id)

    if result.get("status") not in ("completed", "complete", "done"):
        print(f"[ERROR] Research failed: {result}")
        return None

    # Get the result content
    raw_content = ""

    # Try to get content from result
    if "result" in result:
        raw_content = result["result"]
    elif "output" in result:
        raw_content = result["output"]
    elif "content" in result:
        raw_content = result["content"]
    elif "files" in result:
        # Download first file
        files = result["files"]
        if files and len(files) > 0:
            file_id = files[0].get("id") or files[0].get("file_id")
            if file_id:
                raw_content = download_file(file_id) or ""

    # Parse into structured report
    report = parse_research_report(raw_content, task_id)

    # Save to cache
    save_report(report)

    return report


def run_test():
    """Run a simple test task."""
    print("[INFO] Running test task...")

    if not MANUS_API_KEY:
        print("[ERROR] MANUS_API_KEY not set. Please add it to your .env file.")
        print("  Example: MANUS_API_KEY=your_api_key_here")
        return

    # Create a simple test task
    task_id = create_research_task(
        topic="test",
        genres=["Fantasy"],
        platforms=["Webnovel"],
    )

    if task_id:
        print(f"[SUCCESS] Test task created: {task_id}")
        print("[INFO] Use this task ID to check status via the API")
    else:
        print("[ERROR] Failed to create test task")


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Web novel market research using Manus AI"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a test task to verify API connectivity",
    )
    parser.add_argument(
        "--genres",
        nargs="+",
        help="Genres to focus on (e.g., Fantasy Romance Sci-Fi)",
    )
    parser.add_argument(
        "--platforms",
        nargs="+",
        help="Platforms to analyze",
    )
    parser.add_argument(
        "--list-reports",
        action="store_true",
        help="List all cached reports",
    )

    args = parser.parse_args()

    if args.test:
        run_test()
    elif args.list_reports:
        reports = load_reports()
        if reports:
            print(f"\nFound {len(reports)} cached reports:\n")
            for r in reports:
                print(f"  - {r['id']}: {r['title']} ({r['created_at']})")
                print(f"    {r['summary']}\n")
        else:
            print("No cached reports found")
    else:
        report = run_research(
            genres=args.genres,
            platforms=args.platforms,
        )
        if report:
            print("\n" + "=" * 60)
            print(f"Research Complete: {report.title}")
            print("=" * 60)
            print(f"Summary: {report.summary}")
            print(f"Genres: {len(report.genres)}")
            print(f"Novels: {len(report.trending_novels)}")
            print(f"Trailer Ideas: {len(report.trailer_suggestions)}")
            print("=" * 60)


if __name__ == "__main__":
    main()
