from __future__ import annotations

from typing import List, Dict, Literal
from pathlib import Path
import json

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai


# ============ 数据模型 ============

TraitCategory = Literal[
    "physical_appearance",  # 身材, 脸型, 五官, 年龄感
    "temperament",          # 气质, 神态,给人的感觉
    "hairstyle",            # 头发长度,颜色,发型
    "clothing",             # 服饰风格, 材质, 颜色
    "status",               # 身份地位, 当前状态(病重, 负伤等)
    "other",                # 其他人物相关描述
]

Importance = Literal[
    "main_protagonist",     # 绝对主角
    "secondary_lead",       # 重要配角 / 双主角
    "supporting",           # 普通配角
    "minor",                # 路人角色
]


class TraitSnippet(BaseModel):
    category: TraitCategory = Field(
        description="Type of trait described in this snippet"
    )
    original_text: str = Field(
        description="Exact quote from the chapter that describes the character"
    )
    normalized: str = Field(
        description="Short normalized description in plain English"
    )


class ChapterCharacterMention(BaseModel):
    canonical_name: str = Field(
        description="Standardized name for this character, e.g. 'Chu Yu'"
    )
    aliases: List[str] = Field(
        description="All alternative names/titles/pronouns clearly referring to this character in THIS chapter"
    )
    importance: Importance = Field(
        description="How important this character is to the OVERALL story, as inferred from this chapter"
    )
    chapter_id: str = Field(
        description="Chapter identifier for traceability"
    )
    chapter_role_summary: str = Field(
        description="1-2 sentences summarizing this character's role and function in this chapter"
    )
    trait_snippets: List[TraitSnippet] = Field(
        description="Concrete descriptive snippets about this character from this chapter"
    )


class ChapterCharactersWithTraits(BaseModel):
    chapter_id: str
    characters: List[ChapterCharacterMention]


class CharacterBaseProfile(BaseModel):
    novel_name: str = Field(
        description="Name of the novel this character is from"
    )
    character_name: str
    aliases: List[str]

    core_appearance: Dict[str, str] = Field(
        description="Stable physical traits that should be consistent in most images, e.g. age range, body type, face, hair"
    )
    baseline_outfit: Dict[str, str] = Field(
        description="Typical clothing style and colours in neutral scenes, not tied to any extreme situation"
    )
    temperament_baseline: List[str] = Field(
        description="Stable personality and temperament traits"
    )
    scene_variants: List[Dict[str, str]] = Field(
        description=(
            "Context specific variants, e.g. 'on deathbed, frail' or "
            "'in battle armor, harsher expression'. Can be empty list."
        )
    )
    supporting_quotes: List[str] = Field(
        description="3-6 original quotes from the novel that best justify this profile"
    )


# ============ Prompt 构造 ============

def build_chapter_prompt(
    novel_title: str,
    chapter_id: str,
    chapter_text: str,
    max_characters: int = 12,
) -> str:
    return f"""
You are an expert literary analyst and character bible writer.

Your task: read ONE chapter of a long novel and:
1) find the characters that matter to the overall story.
2) collect concrete descriptive evidence about their appearance, temperament and clothing.
3) already give a first guess of whether they are potential MAIN characters or only supporting.

Novel title: {novel_title}
Chapter: {chapter_id}

=====================
CHAPTER TEXT
=====================
{chapter_text}

=====================
INSTRUCTIONS
=====================

For this chapter:

1. Identify named characters that appear.
   If multiple names or titles clearly refer to the same person, MERGE them and pick one canonical_name.

2. For EACH character, estimate their importance for the WHOLE STORY. Use:
   - main_protagonist: clearly the central figure, point of view, or emotional core of the book.
   - secondary_lead: very important recurring character, might be co-lead or love interest.
   - supporting: recurring but not central.
   - minor: appears briefly, likely not important for a trailer.

   Use your best judgment from this chapter. You can tag more than one character as main_protagonist or secondary_lead if the story feels like an ensemble, but keep it conservative.

3. Collect descriptive evidence. For each character:
   - Extract 2-6 short quotes that describe:
     - physical_appearance: body, face, age impression, scars.
     - temperament: attitude, aura, how others feel about them.
     - hairstyle: hair length, colour, style.
     - clothing: outfit style, materials, colours.
     - status: social rank, current condition (sick, injured, powerful).
   - For each quote, add a short normalized description in plain English.

4. Prefer to list at most {max_characters} characters in this chapter, focusing on the most important ones for the overall story.

=====================
OUTPUT FORMAT
=====================

You MUST output a single JSON object of type ChapterCharactersWithTraits with fields:
- chapter_id
- characters: an array of ChapterCharacterMention, each with:
  - canonical_name
  - aliases
  - importance
  - chapter_id
  - chapter_role_summary
  - trait_snippets: array of TraitSnippet
    - category (physical_appearance | temperament | hairstyle | clothing | status | other)
    - original_text
    - normalized

Do not output anything outside the JSON.
"""


def build_profile_prompt(
    novel_title: str,
    character_name: str,
    aliases: List[str],
    mentions: List[ChapterCharacterMention],
) -> str:
    # 把所有章节的特征片段和摘要拼成文本, 方便模型做全局总结
    mention_blocks = []
    for m in mentions:
        traits_lines = []
        for t in m.trait_snippets:
            traits_lines.append(
                f"- [{t.category}] original: {t.original_text.strip()}\n  normalized: {t.normalized.strip()}"
            )
        traits_text = "\n".join(traits_lines) if traits_lines else "(no explicit traits given)"

        block = f"""
CHAPTER: {m.chapter_id}
ROLE SUMMARY: {m.chapter_role_summary}

TRAITS:
{traits_text}
"""
        mention_blocks.append(block)

    mentions_text = "\n".join(mention_blocks)

    aliases_str = ", ".join(sorted({a for a in aliases if a}))

    return f"""
You are creating a CHARACTER BASE PROFILE for use in visual development and trailer generation.

Novel: {novel_title}
Character canonical name: {character_name}
Known aliases or titles: {aliases_str if aliases_str else "(none)"}

Below are multiple mentions of this character across different chapters,
including trait snippets and short role summaries:

=====================
MENTIONS AND TRAIT SNIPPETS
=====================
{mentions_text}

=====================
YOUR TASK
=====================

From all this evidence, infer a coherent and STABLE base profile for this character.

1. core_appearance:
   - age_range: how old they seem in the main timeline of the novel.
   - body_type: slim, muscular, average, etc.
   - face: general face shape and key features.
   - hair: usual hair colour, length, and style that should remain consistent.

2. baseline_outfit:
   - style: the typical outfit style in neutral scenes (not extreme situations).
   - materials: fabrics or armour type.
   - colours: main colour palette that fits the novel's tone.
   This baseline outfit is what a portrait or neutral keyframe should use.

3. temperament_baseline:
   - 3-8 adjectives or short phrases that capture their stable personality and aura.

4. scene_variants:
   - Optional list of important context specific looks.
   - Each variant should have:
     - context: short description like 'on deathbed in exile' or 'in battle armour on the front'.
     - changes: how appearance and outfit differ from baseline.
   Only include variants that are clearly and repeatedly described or crucial for the story.

5. supporting_quotes:
   - Select 3-6 of the strongest original quotes from the evidence above
     that best justify your profile and could be reused as reference.

=====================
OUTPUT FORMAT
=====================

You MUST output a single JSON object of type CharacterBaseProfile with fields:
- novel_name
- character_name
- aliases
- core_appearance
- baseline_outfit
- temperament_baseline
- scene_variants
- supporting_quotes

The JSON must be valid and contain no comments or trailing commas.
Do not output anything outside the JSON.
"""


# ============ 调用 Gemini ============

def analyze_chapter_characters(
    client: genai.Client,
    model_name: str,
    novel_title: str,
    chapter_id: str,
    chapter_text: str,
) -> ChapterCharactersWithTraits:
    prompt = build_chapter_prompt(
        novel_title=novel_title,
        chapter_id=chapter_id,
        chapter_text=chapter_text,
    )

    resp = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": ChapterCharactersWithTraits.model_json_schema(),
        },
    )

    raw = getattr(resp, "text", None)
    if raw is None or not raw.strip():
        # 回退到第一个 candidate
        raw = resp.candidates[0].content.parts[0].text

    return ChapterCharactersWithTraits.model_validate_json(raw)


def build_character_profile_from_mentions(
    client: genai.Client,
    model_name: str,
    novel_title: str,
    character_name: str,
    aliases: List[str],
    mentions: List[ChapterCharacterMention],
) -> CharacterBaseProfile:
    prompt = build_profile_prompt(
        novel_title=novel_title,
        character_name=character_name,
        aliases=aliases,
        mentions=mentions,
    )

    resp = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": CharacterBaseProfile.model_json_schema(),
        },
    )

    raw = getattr(resp, "text", None)
    if raw is None or not raw.strip():
        raw = resp.candidates[0].content.parts[0].text

    profile = CharacterBaseProfile.model_validate_json(raw)
    # 手动设置novel_name，因为AI生成的JSON可能不包含这个字段
    profile.novel_name = novel_title
    return profile


# ============ 聚合与主角筛选 ============

def aggregate_characters(
    chapter_results: List[ChapterCharactersWithTraits],
) -> Dict[str, dict]:
    """
    汇总每个人物在全书中的出现信息与重要性统计.
    返回结构:
    {
      "Chu Yu": {
        "aliases": set([...]),
        "chapters_seen": set([...]),
        "importance_counts": { "main_protagonist": int, ... },
        "mentions": [ChapterCharacterMention, ...]
      },
      ...
    }
    """
    char_map: Dict[str, dict] = {}

    for ch in chapter_results:
        for c in ch.characters:
            name = c.canonical_name.strip()
            if not name:
                continue
            if name not in char_map:
                char_map[name] = {
                    "aliases": set(),
                    "chapters_seen": set(),
                    "importance_counts": {
                        "main_protagonist": 0,
                        "secondary_lead": 0,
                        "supporting": 0,
                        "minor": 0,
                    },
                    "mentions": [],
                }
            entry = char_map[name]
            entry["aliases"].update(a.strip() for a in c.aliases if a)
            entry["chapters_seen"].add(c.chapter_id)
            entry["importance_counts"][c.importance] += 1
            entry["mentions"].append(c)

    return char_map


def score_character(entry: dict) -> float:
    counts = entry["importance_counts"]
    # 主角权重高, 再到重要配角
    score = (
        counts["main_protagonist"] * 3.0
        + counts["secondary_lead"] * 2.0
        + counts["supporting"] * 1.0
    )
    # 出现章节越多越重要
    score += len(entry["chapters_seen"]) * 0.5
    return score


def select_main_characters(
    char_map: Dict[str, dict],
    max_main_chars: int = 3,
    min_score: float = 3.0,
):
    scored = []
    for name, entry in char_map.items():
        s = score_character(entry)
        scored.append((name, s, entry))

    scored.sort(key=lambda x: x[1], reverse=True)
    # 过滤掉分数太低的
    scored = [item for item in scored if item[1] >= min_score]
    return scored[:max_main_chars]


# ============ 顶层流程: 直接从小说到主角基底特征 ============

def build_main_character_profiles_from_novel(
    novel_path: Path,
    model_name: str = "gemini-2.5-flash",
    max_chapters_to_scan: int | None = 20,
    max_main_chars: int = 3,
) -> List[CharacterBaseProfile]:
    data = json.loads(novel_path.read_text(encoding="utf-8"))
    novel_title = data.get("name", "Unknown novel")

    # 简单假设结构: volumes[0].chapters[].{name, content}
    volumes = data.get("volumes", [])
    if not volumes:
        raise ValueError("No volumes found in novel JSON")

    chapters_raw = volumes[0].get("chapters", [])
    if max_chapters_to_scan is not None:
        chapters_raw = chapters_raw[:max_chapters_to_scan]

    client = genai.Client()

    chapter_results: List[ChapterCharactersWithTraits] = []

    for ch in chapters_raw:
        chapter_id = ch.get("name") or ch.get("chapter_id") or "Unknown chapter"
        chapter_text = ch.get("content", "")
        print(f"[INFO] Analyzing characters in {chapter_id}...")
        result = analyze_chapter_characters(
            client=client,
            model_name=model_name,
            novel_title=novel_title,
            chapter_id=chapter_id,
            chapter_text=chapter_text,
        )
        chapter_results.append(result)

    # 聚合并自动选主角
    char_map = aggregate_characters(chapter_results)
    main_candidates = select_main_characters(
        char_map,
        max_main_chars=max_main_chars,
        min_score=3.0,
    )

    print("[INFO] Main character candidates:")
    for name, score, entry in main_candidates:
        print(
            f"  - {name}: score={score:.2f}, "
            f"chapters={len(entry['chapters_seen'])}, "
            f"importance_counts={entry['importance_counts']}"
        )

    # 对每个主角候选, 生成基底特征
    profiles: List[CharacterBaseProfile] = []
    for name, score, entry in main_candidates:
        print(f"[INFO] Building base profile for {name}...")
        profile = build_character_profile_from_mentions(
            client=client,
            model_name=model_name,
            novel_title=novel_title,
            character_name=name,
            aliases=list(entry["aliases"]),
            mentions=entry["mentions"],
        )
        profiles.append(profile)

    # 保存
    out_path = novel_path.with_name("character_base_profiles.json")
    out_data = [json.loads(p.model_dump_json(ensure_ascii=False)) for p in profiles]
    out_path.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[INFO] Character base profiles written to {out_path}")

    return profiles


def main():
    load_dotenv()
    novel_path = Path("/Users/lee/Documents/Career/AI/Readgates/novel2trailer/Ghost_Blows_Out_the_Light_II/novel.json")
    build_main_character_profiles_from_novel(
        novel_path=novel_path,
        model_name="gemini-2.5-flash",
        max_chapters_to_scan=20,   # 可以先只扫前 20 章
        max_main_chars=10          # 默认抽 10 个核心人物
    )


if __name__ == "__main__":
    main()
