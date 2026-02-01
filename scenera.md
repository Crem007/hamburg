## Overview

This project transforms novels into AI-generated trailer videos. It extracts key scenes from a novel, creates a trailer structure, generates cinematographic keyframes, produces AI-generated images, converts them to video clips.

## Project Structure

```
hamburg
├── .env                    # API keys (not committed)
├── .gitignore
├── requirements.txt        # Python dependencies
├── scenera.md           # This file
├── backend/
│   ├── api/               # FastAPI backend for Scenera
│   │   └── main.py
│   ├── scripts/           # Pipeline scripts
│   ├── data/              # Input data (JSON files)
│   ├── output/            # Generated files
│   └── video_generator/   # Video generation module
└── frontend/              # Next.js web app
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx           # Video editor
    │   │   ├── generator/         # Generator page
    │   │   ├── market-research/   # Market research dashboard
    │   │   └── launch/            # Launch page
    │   ├── components/
    │   ├── lib/                   # API helpers, types
    │   └── stores/                # Zustand state stores
    ├── public/
    └── package.json
```

## Generator Web App

**What it does**: Takes any text (book excerpt, speech, transcript, article) → extracts key visual scenes → generates images for each scene → displays results in a 2x2 grid.

### Running Generator

```bash
# Terminal 1: Start backend API
cd backend
uvicorn api.main:app --reload
# Runs at http://localhost:8000

# Terminal 2: Start frontend
cd frontend
npm install
npm run dev
# Runs at http://localhost:3000
```

Visit `http://localhost:3000/generator` to use the app.

### Backend API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/extract-scenes` | POST | Extract visual scenes from text using Gemini |
| `/api/generate` | POST | Generate images for scenes using Gemini |
| `/api/regenerate` | POST | Regenerate a single image |
| `/api/book` | GET | Fetch book text from Project Gutenberg |
| `/api/research/start` | POST | Start a new Manus research task |
| `/api/research/status/{task_id}` | GET | Check research task status |
| `/api/research/reports` | GET | List all completed research reports |
| `/api/research/reports/{report_id}` | GET | Get specific research report |

## Pipeline Stages

```
Novel JSON
    ↓
Extract Key Scenes → novel_scenes.json
    ↓
Build World Profile → novel_world_profile.json
    ↓
[build_main_character_profiles.py] Extract Character Traits → character_base_profiles.json
    ↓
Generate Character Portraits → character_portraits/
    ↓
Scene → Trailer Script → trailer_script.json
    ↓
Trailer Beats → Keyframe Plan → keyframe_plan.json
    ↓
Unify Keyframe Style → keyframe_plan_styled.json
    ↓
Generate Keyframe Images → keyframe_images/
    ↓
Extract Image Layers → keyframe_layers/
    ↓
Generate Keyframe Videos → keyframe_videos/
```

## Backend Scripts

| Script | Purpose | API Used |
|--------|---------|----------|
| `novel_world_profile.py` | Analyze novel's world and visual setting | Gemini |
| `novel_scenes_extraction.py` | Extract key narrative scenes | Gemini |
| `build_main_character_profiles.py` | Create character reference documents | Gemini |
| `scene_to_trailer.py` | Convert scenes to trailer beats | Gemini |
| `trailer_to_keyframe.py` | Design keyframes per beat | Gemini |
| `unify_keyframe_style.py` | Apply consistent visual style | Gemini |
| `generate_character_portraits.py` | Generate character portraits | **Gemini** |
| `generate_keyframe_images.py` | Generate keyframe images | **Gemini** |
| `extract_image_layers.py` | Extract image layers | **fal.ai (Qwen Image Layered)** |
| `generate_keyframe_videos.py` | Convert images to videos | **Google Veo 3.1** |
| `market_research.py` | Web novel market research | **Manus AI** |

## API Keys Required

Add these to your `.env` file:

```
GOOGLE_API_KEY=your_google_api_key      # Gemini (text + images) + Veo (video)
FAL_KEY=your_fal_ai_key                 # Qwen (layers)
MANUS_API_KEY=your_manus_api_key        # Manus (market research)
```