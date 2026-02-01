# Scenera

AI-powered application that transforms novels and text into cinematographic trailer videos.

## Overview

Scenera extracts key visual scenes from novels or any text content, generates AI-powered images, decomposes them into layers, and produces cinematic video clips. It includes a web-based editor for refining and composing final videos, plus market research capabilities for web novel trends.

## Features

- **Text-to-Visual Narrative**: Automatically generates cinematic images from any text
- **Multiple Art Styles**: Cinematic, Anime, Oil Painting, Photorealistic, Watercolor, Noir
- **Web-Based Editor**: Interactive Pixi.js canvas editor for video composition
- **Image Decomposition**: Breaks images into layers for sophisticated video generation
- **Market Research**: Analyzes web novel trends using Manus AI
- **Project Gutenberg Integration**: Fetch public domain novels for processing
- **Real-time Updates**: Streaming progress during generation

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **AI Services**: Google Gemini (text/image), Google Veo (video), fal.ai Qwen (image layers)
- **Libraries**: Pydantic, httpx, Pillow, aiofiles

### Frontend
- **Framework**: Next.js 15 (React 19)
- **Language**: TypeScript
- **Styling**: Tailwind CSS 4
- **Graphics**: Pixi.js
- **State**: Zustand

## Project Structure

```
Hamburg/
├── backend/
│   ├── api/main.py              # FastAPI endpoints
│   ├── scripts/                  # Pipeline processing scripts
│   ├── data/                     # Input JSON files
│   ├── output/                   # Generated content
│   └── video_generator/          # Video generation module
├── frontend/
│   └── src/
│       ├── app/                  # Next.js pages
│       ├── components/editor/    # Pixi.js editor
│       ├── lib/                  # API clients & types
│       └── stores/               # Zustand stores
├── requirements.txt
└── .env                          # API keys (not committed)
```

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 18+
- API keys: Google API, fal.ai, Manus AI

### Environment Setup

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_google_api_key
FAL_KEY=your_fal_api_key
MANUS_API_KEY=your_manus_api_key
```

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn api.main:app --reload
```

Server runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

App runs at `http://localhost:3000`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/extract-scenes` | POST | Extract key visual scenes from text |
| `/api/generate` | POST | Generate images for scenes |
| `/api/regenerate` | POST | Regenerate a single image |
| `/api/book` | GET | Fetch book from Project Gutenberg |
| `/api/demo-generate` | POST | Full pipeline demo (streaming) |
| `/api/research/start` | POST | Start market research task |
| `/api/research/status/{task_id}` | GET | Check research task status |
| `/api/research/reports` | GET | List completed reports |

## Pipeline Architecture

```
Novel/Text Input
       ↓
Extract Scenes → World Profile → Character Extraction
       ↓
Character Portraits → Trailer Script → Keyframe Plan
       ↓
Style Unification → Generate Images → Extract Layers
       ↓
Generate Videos → Final Composition (Editor)
```

## Pages

- `/` - Main video editor
- `/editor` - Editor page
- `/market-research` - Market research dashboard
- `/launch` - Final output and distribution

## License

MIT
