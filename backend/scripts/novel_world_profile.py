from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai


# ============ 数据模型 ============

class ChapterWorldHints(BaseModel):
    novel_name: str
    chapter_id: str
    time_and_era: str = Field(
        description="How this chapter implicitly or explicitly suggests the time period or era."
    )
    geography_and_region: str = Field(
        description="What this chapter implies about geography, climate and region style."
    )
    social_structure: str = Field(
        description="What this chapter suggests about power structures, classes, institutions."
    )
    tech_and_warfare: str = Field(
        description="Weapons, technology, transport inferred from this chapter."
    )
    typical_locales: List[str] = Field(
        description="Concrete locations that appear in this chapter, described visually."
    )
    clothing_and_wardrobe: Dict[str, str] = Field(
        description=(
            "Clothing hints grouped by role, if present in this chapter. "
            "For example 'noblewoman', 'soldier', 'general', 'commoner'."
        )
    )
    color_and_mood: str = Field(
        description="Dominant colours and emotional atmosphere in this chapter."
    )
    visual_motifs: List[str] = Field(
        description="Symbolic props or imagery that could recur visually."
    )
    global_style: str = Field(
        description="(Optional) Overall style hints for the story world."
    )


class WorldProfile(BaseModel):
    novel_name: str
    world_summary: str = Field(
        description="One paragraph summary of the story world, era and main conflicts."
    )
    era_label: str = Field(
        description="Loose era label, for example 'fictional dynasty inspired by late imperial China'."
    )
    region_style: str = Field(
        description="Cultural and geographic flavour, for example 'northern frontier, walled capital city'."
    )
    tech_level: str = Field(
        description="Approximate technology level, for example 'pre industrial cold weapons, horses, no firearms'."
    )
    social_structure: str = Field(
        description="Social structure, for example 'emperor, imperial court, noble houses, military families, commoners'."
    )
    typical_locales: List[str] = Field(
        description="List of typical locations in the story, in visual terms."
    )
    wardrobe_guide: Dict[str, str] = Field(
        description="Visual clothing guide per role, for example 'noblewoman', 'general', 'soldier', 'commoner'."
    )
    color_and_mood: str = Field(
        description="Global colour palette and emotional tone of the story world."
    )
    visual_motifs: List[str] = Field(
        description="Recurring visual motifs, symbols or props."
    )
    global_style: str = Field(
        description="Overall style hints for the story world, to guide image generation."
    )
    


# ============ 阶段 1: 每章提取世界观线索 ============

def build_chapter_hints_prompt(
    novel_name: str,
    chapter_id: str,
    chapter_text: str,
) -> str:
    return f"""
You are a worldbuilding analyst.

You will read ONE chapter of a long novel and extract only the information that helps
reconstruct the STORY WORLD and VISUAL SETTING.

Novel title: {novel_name}
Chapter: {chapter_id}

=====================
CHAPTER TEXT
=====================
{chapter_text}

=====================
INSTRUCTIONS
=====================

From this chapter, infer and summarise ONLY what contributes to the worldbuilding:

1. time_and_era:
   - What does this chapter suggest about the historical period or era.
   - For example: 'fictional imperial dynasty with pre gunpowder warfare' or 'modern city'.

2. geography_and_region:
   - Clues about geography, climate and region style, for example:
     'northern frontier with cold climate and snow', 'walled capital city', 'river basin'.

3. social_structure:
   - Power structures and social layers visible in this chapter.
   - For example 'emperor, imperial court, noble houses, generals, commoners, servants'.

4. tech_and_warfare:
   - Weapons, transport, tools implied in this chapter.
   - For example 'swords, spears, horses, no firearms', or 'gunpowder artillery', etc.

5. typical_locales:
   - 2 to 6 concrete locations appearing in this chapter, described visually.
   - For example 'general's mansion inner courtyard', 'ancestral hall with tablets', 'battlefield at snow covered pass'.

6. clothing_and_wardrobe:
   - Group clothing hints by role if possible, for example:
     - noblewoman
     - young general
     - soldiers
     - imperial officials
     - commoners
   - For each role mentioned in this chapter, describe fabrics, layers, silhouettes and typical colours.

7. color_and_mood:
   - Dominant colours and emotional atmosphere suggested by this chapter.
   - For example 'muted earth tones with flashes of crimson, tense but restrained'.

8. visual_motifs:
   - 3 to 8 symbolic props or visual motifs that could be reused.
   - For example 'banners in the wind, blood on snow, ancestral tablets, lanterns in rain'.
9. global_style:
    - Overall style hints for the story world, to guide image generation.MUST be consistent with the era and region.

If some sections are not clearly described in this chapter, write a short sentence saying
'not clearly specified in this chapter' rather than invent wildly new content.

=====================
OUTPUT FORMAT
=====================

You MUST output a single JSON object of type ChapterWorldHints with fields:
- novel_name
- chapter_id
- time_and_era
- geography_and_region
- social_structure
- tech_and_warfare
- typical_locales
- clothing_and_wardrobe
- color_and_mood
- visual_motifs
- global_style

The JSON must be valid and contain no comments or trailing commas.
Do not output anything outside the JSON.
"""


def extract_chapter_world_hints(
    client: genai.Client,
    model_name: str,
    novel_name: str,
    chapter_id: str,
    chapter_text: str,
) -> ChapterWorldHints:
    prompt = build_chapter_hints_prompt(
        novel_name=novel_name,
        chapter_id=chapter_id,
        chapter_text=chapter_text,
    )

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": ChapterWorldHints.model_json_schema(),
        },
    )

    raw = getattr(response, "text", None)
    if raw is None or not raw.strip():
        raw = response.candidates[0].content.parts[0].text

    hints = ChapterWorldHints.model_validate_json(raw)

    # 确保 novel_name 填好
    if not hints.novel_name:
        hints.novel_name = novel_name

    return hints


# ============ 阶段 2: 汇总所有章节 hints → WorldProfile ============

def build_world_profile_prompt_from_hints(
    novel_name: str,
    novel_summary: str,
    hints_list: List[ChapterWorldHints],
) -> str:
    # 把每章 hints 拼成一个文本
    blocks = []
    for h in hints_list:
        block = f"""
CHAPTER: {h.chapter_id}

time_and_era:
{h.time_and_era}

geography_and_region:
{h.geography_and_region}

social_structure:
{h.social_structure}

tech_and_warfare:
{h.tech_and_warfare}

typical_locales:
- """ + "\n- ".join(h.typical_locales) + f"""

clothing_and_wardrobe:
{json.dumps(h.clothing_and_wardrobe, ensure_ascii=False)}

color_and_mood:
{h.color_and_mood}

visual_motifs:
- """ + "\n- ".join(h.visual_motifs) + "\n"
        blocks.append(block)

    hints_text = "\n\n".join(blocks)

    return f"""
You are a senior worldbuilding and visual development specialist.

You are given worldbuilding hints extracted chapter by chapter from a long novel.
Now you must synthesise a SINGLE coherent WORLD PROFILE for visual use
in character design and trailer keyframes.

=====================
NOVEL META
=====================
Title: {novel_name}

High level summary:
{novel_summary}

=====================
CHAPTER WORLD HINTS (AGGREGATED)
=====================
{hints_text}

=====================
INSTRUCTIONS
=====================

Using ALL the information above:

1. world_summary.
   - One concise paragraph summarising the world, time period and main conflicts.
   - It should be visually useful and grounded in the hints.

2. era_label.
   - A short era description, for example
     'fictional dynasty inspired by late imperial China'
     or 'low fantasy kingdom with medieval tech'.

3. region_style.
   - Cultural and geographic flavour, for example
     'northern frontier with snow covered fortresses and a walled capital city'.

4. tech_level.
   - Approximate technology level, for example
     'pre industrial cold weapons, horses, no firearms'
     or 'early gunpowder siege weapons'.

5. social_structure.
   - A concise description of the social and power structure.
   - Mention key layers like emperor, court, noble houses, generals, soldiers, commoners.

6. typical_locales.
   - A list of 5 to 10 typical locations, described visually.
   - You can merge similar locales across chapters.

7. wardrobe_guide.
   - A mapping from role to visual clothing description.
   - At least include keys:
     - noblewoman
     - young general
     - soldiers
     - imperial officials
     - commoners
   - For each, describe fabrics, layers, silhouettes and typical colours.
   - Be consistent with the era and region.

8. color_and_mood.
   - Overall colour palette and emotional tone of the story world.
   - This will guide the look of all images.

9. visual_motifs.
   - A list of 6 to 12 recurring symbolic props or visual motifs that fit the story.
   - These should be reusable across many scenes.

10. global_style.
    - Overall style hints for the story world, to guide image generation.

=====================
OUTPUT FORMAT
=====================

You MUST output a single JSON object of type WorldProfile with fields:
- novel_name
- world_summary
- era_label
- region_style
- tech_level
- social_structure
- typical_locales
- wardrobe_guide
- color_and_mood
- visual_motifs
- global_style

The JSON must be valid and must not contain comments or trailing commas.
Do not output anything outside the JSON.
"""


def build_world_profile_from_hints(
    client: genai.Client,
    model_name: str,
    novel_name: str,
    novel_summary: str,
    hints_list: List[ChapterWorldHints],
) -> WorldProfile:
    prompt = build_world_profile_prompt_from_hints(
        novel_name=novel_name,
        novel_summary=novel_summary,
        hints_list=hints_list,
    )

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": WorldProfile.model_json_schema(),
        },
    )

    raw = getattr(response, "text", None)
    if raw is None or not raw.strip():
        raw = response.candidates[0].content.parts[0].text

    profile = WorldProfile.model_validate_json(raw)

    if not profile.novel_name:
        profile.novel_name = novel_name

    return profile


# ============ 总流程 ============

def build_world_profile_two_stage(
    novel_path: Path,
    output_path: Path,
    model_name: str = "gemini-2.5-flash",
    max_chapters: int | None = 20,
) -> None:
    """
    两阶段:
    1. 逐章提取 ChapterWorldHints. 每次只输入一章, 不会爆 context.
    2. 汇总所有 hints, 再生成最终 WorldProfile.
    """
    load_dotenv()
    client = genai.Client()

    data = json.loads(novel_path.read_text(encoding="utf-8"))
    novel_name = data.get("name") or data.get("title") or "Unknown novel"
    novel_summary = data.get("summary", "")

    volumes = data.get("volumes", [])
    if not volumes:
        raise ValueError("novel.json 中未找到 volumes 字段")

    chapters = volumes[0].get("chapters", [])
    if not chapters:
        raise ValueError("novel.json 中 volumes[0].chapters 为空")

    if max_chapters is not None:
        chapters = chapters[:max_chapters]

    hints_list: List[ChapterWorldHints] = []

    # 阶段一: 每章单独提取世界观线索
    for ch in chapters:
        chapter_id = ch.get("name") or ch.get("chapter_id") or "Unknown chapter"
        chapter_text = ch.get("content", "")

        print(f"[INFO] Extracting world hints from {chapter_id}...")
        hints = extract_chapter_world_hints(
            client=client,
            model_name=model_name,
            novel_name=novel_name,
            chapter_id=chapter_id,
            chapter_text=chapter_text,
        )
        hints_list.append(hints)

    # 阶段二: 汇总成一个全局 WorldProfile
    print("[INFO] Building global world profile from chapter hints...")
    world_profile = build_world_profile_from_hints(
        client=client,
        model_name=model_name,
        novel_name=novel_name,
        novel_summary=novel_summary,
        hints_list=hints_list,
    )

    output_path.write_text(
        world_profile.model_dump_json(ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[INFO] World profile written to {output_path}")


def main():
    base_dir = Path(__file__).resolve().parent
    novel_path = base_dir / "novel.json"
    output_path = base_dir / "novel_world_profile.json"

    if not novel_path.exists():
        raise FileNotFoundError(f"novel.json not found at {novel_path}")

    build_world_profile_two_stage(
        novel_path=novel_path,
        output_path=output_path,
        model_name="gemini-2.5-flash",
        max_chapters=20,   # 这里控制最多扫多少章
    )


if __name__ == "__main__":
    main()
