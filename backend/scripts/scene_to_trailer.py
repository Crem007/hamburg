from typing import List, Literal, Optional
from pydantic import BaseModel, Field
import json
from pathlib import Path
from google import genai
from dotenv import load_dotenv


BeatRole = Literal["hook", "conflict", "escalation", "cliffhanger"]

class TrailerBeat(BaseModel):
    beat_id: str = Field(
        description="Beat identifier, e.g. 'B1','B2','B3','B4'"
    )
    role: BeatRole = Field(
        description="Position in trailer arc: hook, conflict, escalation, or cliffhanger"
    )
    duration_sec: float = Field(
        description="Estimated screen time for this beat, in seconds"
    )
    source_scenes: List[str] = Field(
        description="List of scene references in format 'chapter_id_sScene_id', e.g. ['v01_ch001_s1', 'v01_ch001_s2']"
    )
    characters: List[str] = Field(
        description="List of main character names appearing in this beat, e.g. ['Chu Yu', 'Wei Yun']. Used to reference character portraits in later stages."
    )
    logline: str = Field(
        description="One-line description of what the audience should feel/understand in this beat"
    )
    visual_idea: str = Field(
        description="High-level idea of the visuals in this beat (not shot list, just concept)"
    )
    key_moments: List[str] = Field(
        description="2-4  bullet points describing specific key moments inside this beat,mainly about visuals, could include actions or expressions or environment details"
    )
    dialogue_or_text: List[str] = Field(
        description="Third-person narrative lines or on-screen text snippets to use in this beat. Write as a narrator telling the story (e.g., 'She never imagined that one choice would change everything...', 'In a world where...'), NOT as character dialogue."
    )
    spoiler_level: Literal["none", "light", "medium", "heavy"] = Field(
        description="How spoiler-y this beat is with respect to the full story"
    )
    reasoning: str = Field(
        description="Short explanation why this scene choice and beat design will work for the target audience"
    )


class TrailerScript(BaseModel):
    novel_id: str = Field(
        description="Id or name of the novel"
    )
    title: str = Field(
        description="Title of the novel"
    )
    target_audience: str = Field(
        description="Short description of the target audience in marketing terms"
    )
    platform: str = Field(
        description="Platform name, e.g. 'douyin','bilibili','youtube_short'"
    )
    max_duration_sec: int = Field(
        description="Maximum allowed trailer duration in seconds"
    )
    style_tags: List[str] = Field(
        description="Style tags, e.g. ['epic','romantic','dark','slow_burn']"
    )
    beats: List[TrailerBeat] = Field(
        description="Ordered list of 4-6 beats forming the trailer spine"
    )
    notes_for_storyboard: str = Field(
        description="Global guidance for storyboard / keyframe design"
    )




def build_trailer_prompt(
    novelscenes_json: str,
    novel_id: str,
    title: str,
    platform: str = "tiktok",
    max_duration_sec: int = 30,
    ) -> str:


    prompt = f"""
You are a **senior trailer creative director** and **narrative editor** working for a top streaming platform.
You design emotionally gripping {max_duration_sec}-second book trailers for {platform} based on detailed scene analysis.

====================
YOUR TASK
====================
1) **ANALYZE THE SCENES**: Read the provided novel scenes carefully and identify:
   - The core emotional hook that will resonate most with the target audience
   - The most visually striking and emotionally powerful moments
   - The story's unique selling points (USPs) based on genre, themes, and character dynamics
   - The target demographic most likely to engage with this content

2) **CREATE A TRAILER STRATEGY**: Based on your analysis, determine:
   - What is the ONE central emotional/conceptual hook to sell?
   - Which 3-6 key selling points will attract viewers?
   - What spoiler policy to follow (reveal early setup only, or hint at mid-story turns?)
   - What visual style tags fit this story (e.g., epic, romantic, dark, suspenseful)

3) **DESIGN THE TRAILER**: Pick and combine 4-6 scenes into a compelling {max_duration_sec}-second trailer with:
   - **Hook** (5-8 sec): Grab attention immediately with the most striking visual or emotional moment
   - **Conflict** (6-10 sec): Establish the core tension or problem
   - **Escalation** (8-12 sec): Build emotional intensity, show stakes rising
   - **Cliffhanger** (3-5 sec): End on a powerful question or promise that demands continuation

====================
INPUT: NOVEL SCENES
====================

novel_id: {novel_id}
title: {title}
platform: {platform}
max_duration_sec: {max_duration_sec}

Here is the full NovelScenes JSON with all chapters and scenes:
{novelscenes_json}

====================
OUTPUT REQUIREMENTS
====================

You MUST output a valid JSON object matching the `TrailerScript` schema with these fields:

- **novel_id**: "{novel_id}"
- **title**: "{title}"
- **target_audience**: Your analysis of who will love this story (be specific: age, gender, interests)
- **platform**: "{platform}"
- **max_duration_sec**: {max_duration_sec}
- **style_tags**: 3-5 visual/emotional style tags you've chosen
- **beats**: Array of 4-6 TrailerBeat objects, each with:
  - beat_id (e.g., "B1", "B2", ...)
  - role (hook/conflict/escalation/cliffhanger)
  - duration_sec (sum should be ≤ {max_duration_sec})
  - source_scenes (array of scene references in format "chapter_id_sScene_id", e.g. ["v01_ch001_s1", "v01_ch002_s3"])
  - characters (array of main character names appearing in this beat, e.g. ["Chu Yu", "Wei Yun"]. Extract from the characters field in the source scenes.)
  - logline (what audience should feel/understand)
  - visual_idea (high-level visual concept)
  - key_moments (2-4 specific visual moments with actions/expressions/environment)
  - dialogue_or_text (0-2 powerful third-person narrative lines that tell the story as a narrator, e.g., 'She never knew...', 'In a world where...', 'But fate had other plans...', dialogue should respect the original tone and style of the novel)
  - spoiler_level (none/light/medium/heavy)
  - reasoning (why this beat works for the target audience)
- **notes_for_storyboard**: Global guidance for visual execution

====================
CRITICAL CONSTRAINTS
====================

- Only use scenes that actually exist in the provided JSON
- Reference scenes using the format: "chapter_id_sScene_id" (e.g., "v01_ch001_s1", "v01_ch002_s3")
- Each scene has a chapter_id (like "v01_ch001") and scene_id (like "1", "2", "3")
- Combine them as: chapter_id + "_s" + scene_id
- Each beat must flow naturally into the next
- Keep total duration at or under {max_duration_sec} seconds
- Be strategic about spoilers
- The trailer should leave viewers wanting more, not satisfied

Output ONLY valid JSON. No commentary outside the JSON object.
"""
    
    return prompt


def generate_trailer_script_from_scenes(
    scenes_path: Path,
    output_path: Path,
    platform: str = "tiktok",
    max_duration_sec: int = 30,
    model_name: str = "gemini-3-pro-preview",
    ):

    # 读情景表 JSON
    novel_scenes = json.loads(scenes_path.read_text(encoding="utf-8"))

    # 这里用 bookCode 或 name 做 novel_id
    novel_id = novel_scenes.get("novel_id") or novel_scenes.get("metadata", {}).get("bookCode") \
               or novel_scenes.get("title") or "unknown_novel"

    title = novel_scenes.get("title") or "unknown_title"
    print(f"[INFO] Generating trailer for novel: {title}")
    print(f"[INFO] Platform: {platform}, Max duration: {max_duration_sec}s")

    client = genai.Client()

    # 为了结构清晰, 把 NovelScenes 再 dump 一次, 确保是干净 JSON 字符串
    novelscenes_json_str = json.dumps(novel_scenes, ensure_ascii=False)

    prompt = build_trailer_prompt(
        novelscenes_json=novelscenes_json_str,
        novel_id=novel_id,
        title=title,
        platform=platform,
        max_duration_sec=max_duration_sec,
    )

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": TrailerScript.model_json_schema(),
        },
    )

    raw = getattr(response, "text", None)
    if raw is None or not raw.strip():
        # 兜底
        raw = response.candidates[0].content.parts[0].text

    # 解析成 TrailerScript, 顺便做 schema 校验
    trailer_script = TrailerScript.model_validate_json(raw)

    # 写到文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(
            json.loads(trailer_script.model_dump_json(ensure_ascii=False)),
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"[INFO] Trailer script written to {output_path}")






def main():
    load_dotenv()
    
    scenes_path = Path("/Users/lee/Documents/Career/AI/Readgates/novel2trailer/Ghost_Blows_Out_the_Light_II/novel_scenes.json")
    output_path = Path("/Users/lee/Documents/Career/AI/Readgates/novel2trailer/Ghost_Blows_Out_the_Light_II/trailer_script.json")

    generate_trailer_script_from_scenes(
        scenes_path=scenes_path,
        output_path=output_path,
        platform="tiktok",
        max_duration_sec=30,
        model_name="gemini-3-pro-preview",
    )

if __name__ == "__main__":
    main() 