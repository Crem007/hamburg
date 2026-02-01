"""
统一一个 trailer 内所有 keyframe 的图像风格:
1) 从 keyframe_plan.json 提取所有 keyframe
2) 让 Gemini 生成一个 TrailerStyleGuide（参考 keyframe_plan + novel_world_profile）
3) 根据 StyleGuide 重写每个 keyframe 的 image_prompt
4) 输出新的 keyframe_plan_styled.json
"""

from pathlib import Path
from typing import List
import os
import sys
import time
import json

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai.errors import ServerError


# ---------- 复用你的 Keyframe 结构 ----------

class Keyframe(BaseModel):
    kf_id: str
    beat_id: str
    order_in_beat: int
    suggested_duration_sec: float
    shot_type: str
    camera_angle: str
    composition: str
    action: str
    emotion_tags: List[str]
    characters: List[str]
    story_grounding: dict
    dialogue_or_text: str
    image_prompt: str  # 来自 003 的“内容向” prompt


class KeyframePlan(BaseModel):
    novel_id: str
    title: str
    keyframes: List[Keyframe]


# ---------- StyleGuide 结构 ----------

class CharacterStyle(BaseModel):
    name: str = Field(
        description="Character name as used in prompts, e.g. 'Chu Yu', 'Wei Yun'"
    )
    role: str = Field(
        description="Short role label, e.g. 'heroine', 'young general', 'rival', 'mentor'"
    )
    visual_description: str = Field(
        description="Canonical visual description: age, body type, face, hair, clothing motif, color accents"
    )


class GlobalStyle(BaseModel):
    rendering_style: str = Field(
        description="Overall rendering style, e.g. 'cinematic digital painting inspired by Chinese historical epics'"
    )
    lighting_style: str = Field(
        description="Typical lighting: e.g. 'warm directional sunlight with soft shadows and atmospheric haze'"
    )
    color_palette: str = Field(
        description="Dominant colors and contrasts used throughout the trailer"
    )
    environment_style: str = Field(
        description="Typical environments: e.g. 'courtyards, ancestral halls, battlefields, city gates'"
    )
    notes: str = Field(
        description="Any additional rules for style consistency"
    )


class TrailerStyleGuide(BaseModel):
    novel_id: str
    title: str
    global_style: GlobalStyle
    characters: List[CharacterStyle]


# ---------- 构建 StyleGuide prompt 的函数 ----------

def build_style_guide_prompt(
    plan: KeyframePlan,
    world_profile: dict | None = None,
) -> str:
    """
    让 Gemini 读完整个 keyframe_plan + novel_world_profile，抽取统一 Style Guide
    当前 keyframe 的 image_prompt 是“内容描述为主”，几乎不含画风词
    """

    # 把每个 keyframe 压缩成短 block
    kf_blocks = []
    for kf in plan.keyframes:
        emo = ", ".join(kf.emotion_tags)
        chars = ", ".join(kf.characters) if kf.characters else "unknown"
        block = f"""
[Keyframe {kf.kf_id} | beat {kf.beat_id}]
- shot_type: {kf.shot_type}
- characters: {chars}
- emotion_tags: [{emo}]
- action: {kf.action}
- original_image_prompt (content-focused, low-style):
  {kf.image_prompt}
"""
        kf_blocks.append(block)

    kf_summary_text = "\n".join(kf_blocks)

    # 把 novel_world_profile 压成一段文本
    world_profile_text = ""
    if world_profile:
        # 尽量利用字段, 但也保底打印整个 JSON
        title = world_profile.get("novel_name") or world_profile.get("title") or ""
        world_summary = world_profile.get("world_summary", "")
        era_label = world_profile.get("era_label", "")
        region_style = world_profile.get("region_style", "")
        tech_level = world_profile.get("tech_level", "")
        social_structure = world_profile.get("social_structure", "")
        typical_locales = world_profile.get("typical_locales", [])
        wardrobe_guide = world_profile.get("wardrobe_guide", {})
        color_and_mood = world_profile.get("color_and_mood", "")
        visual_motifs = world_profile.get("visual_motifs", [])

        world_profile_text = f"""
====================
NOVEL WORLD PROFILE (pre-analysed)
====================
Title: {title}

World summary:
{world_summary}

Era label:
{era_label}

Region style:
{region_style}

Technology level:
{tech_level}

Social structure:
{social_structure}

Typical locales:
- {chr(10) + '- '.join(typical_locales) if typical_locales else "[none listed]"}

Wardrobe guide (per role):
{json.dumps(wardrobe_guide, ensure_ascii=False, indent=2)}

Global colour & mood:
{color_and_mood}

Recurring visual motifs:
- {chr(10) + '- '.join(visual_motifs) if visual_motifs else "[none listed]"}

Raw world_profile JSON:
{json.dumps(world_profile, ensure_ascii=False, indent=2)}
"""

    prompt = f"""
You are a senior visual development director for a book trailer.

You are given:
- A set of storyboard keyframes for ONE trailer.
- A pre-analysed NOVEL WORLD PROFILE that describes the historical era, region flavour, social structure,
  typical locations, wardrobe guide and global colour/mood of the story.

Each keyframe already has:
- a textual image_prompt (currently content-focused, with little or no rendering style)
- basic cinematography info (shot_type, camera_angle, composition, action, emotion_tags)
- a list of characters appearing in the frame

Problem:
- Each image_prompt was generated independently from different novel excerpts.
- At this stage, prompts mainly describe WHO/WHERE/DOING WHAT, but lack a strong unified rendering style.
- Without a unified style guide, the final images may look inconsistent in art style and character design.

Your job:
1) Combine the NOVEL WORLD PROFILE with the keyframe content to infer ONE unified visual style for the entire trailer.
2) Infer consistent canonical visual descriptions for all recurring main characters.
3) Return a structured TrailerStyleGuide object.

The TrailerStyleGuide must:
- Respect the NOVEL WORLD PROFILE: era, region style, tech level, social structure, typical locales,
  wardrobe guide and global colour/mood.
- Set rules for:
  - rendering_style (e.g. 'cinematic digital painting inspired by Chinese historical epics')
  - lighting_style (e.g. 'warm directional sunlight, soft shadows, subtle atmospheric haze')
  - color_palette (e.g. 'deep reds and muted golds contrasted with cool stone and mist')
  - environment_style (typical locations across the trailer)
  - notes (any extra rules for consistency: e.g. 'faces realistic, subtle painterly texture, no anime, no cartoon')
- For each important recurring character (at minimum: heroine, young general, major love interest, key antagonists if present):
  - Give a stable, specific visual_description: age range, build, facial features, hair style, base outfit / armor / robe motif, accent colors.
  - These descriptions must be compatible with the wardrobe_guide and world setting.

Important:
- Abstract away from frame-specific poses or one-off costumes.
- Focus on what should remain consistent across the whole trailer.
- You may refine or upgrade the raw content prompts into a richer, more cinematic style,
  but keep them within the grounded world profile.

Keyframe plan meta:
- novel_id: {plan.novel_id}
- title: {plan.title}
- number of keyframes: {len(plan.keyframes)}

{world_profile_text}

====================
KEYFRAME OVERVIEW (content-focused prompts)
====================
{kf_summary_text}

Now analyse the world profile and ALL the keyframes, and return a single JSON object of type TrailerStyleGuide.
The JSON must be valid and contain no comments.
"""
    return prompt


# ---------- 构建 rewrite prompt 的函数 ----------

def build_rewrite_prompt(
    style: TrailerStyleGuide,
    kf: Keyframe,
) -> str:
    emo = ", ".join(kf.emotion_tags)
    chars = ", ".join(kf.characters) if kf.characters else "unknown"

    prompt = f"""
You are a senior storyboard artist.

You are given:
1) A unified TrailerStyleGuide for one trailer.
2) One specific keyframe (with cinematography and original image_prompt).

Your task:
- Rewrite ONLY the image_prompt for this keyframe.
- Keep:
  - the same narrative moment and action
  - the same shot_type, camera_angle and composition intent
  - the same emotional tone
  - the same set of characters present in the scene
- Enforce:
  - the global rendering_style, lighting_style, color_palette, environment_style and notes from the style guide
  - stable, canonical character designs from the style guide (faces, age, hair, outfit motif and colors)

Original image_prompt is mostly content-focused (who/where/doing what).
If it contains any rendering or art style words (e.g. 'photorealistic', 'anime', 'cinematic still', '8k'),
you must IGNORE or override them with the TrailerStyleGuide style.

DO NOT:
- Invent new outfits that contradict the character's canonical style.
- Change characters' apparent age or core physical traits.
- Change the basic environment type if it is clearly implied in the original prompt.
- Describe it as a photograph or film still. It must be clearly a hand-painted digital illustration.

Global rendering constraints:
- It must be a hand-painted digital illustration, not a photograph.
- Visible painterly brushstrokes and slight canvas-like texture.
- Cinematic composition is allowed, but do NOT call it a 'film still' or 'photo'.
- Avoid wording that suggests pure photorealism.

Output:
- A SINGLE string: the new image_prompt, self-contained and ready for an image model.
- Do NOT include JSON, field names, or any commentary. Only the prompt.

====================
TRAILER STYLE GUIDE (for this whole trailer)
====================
{style.model_dump_json(indent=2, ensure_ascii=False)}

====================
KEYFRAME META
====================
- kf_id: {kf.kf_id}
- beat_id: {kf.beat_id}
- shot_type: {kf.shot_type}
- camera_angle: {kf.camera_angle}
- composition: {kf.composition}
- action: {kf.action}
- emotion_tags: [{emo}]
- characters: {chars}
-dialogue_or_text: {kf.dialogue_or_text}


Original image_prompt (content-focused):
{kf.image_prompt}

Now rewrite the image_prompt according to the style guide.
Return only the rewritten prompt as plain text.
"""
    return prompt


# ---------- 主流程 ----------

def main():
    load_dotenv()

    base_dir = Path("/Users/lee/Documents/Career/AI/Readgates/novel2trailer/Ghost_Blows_Out_the_Light_II")

    keyframe_plan_path = base_dir / "keyframe_plan.json"
    world_profile_path = base_dir / "novel_world_profile.json"
    output_path = base_dir / "keyframe_plan_styled.json"

    raw_plan = json.loads(keyframe_plan_path.read_text(encoding="utf-8"))
    plan = KeyframePlan.model_validate(raw_plan)

    # 读取 novel_world_profile.json（如果存在）
    world_profile = None
    if world_profile_path.exists():
        world_profile = json.loads(world_profile_path.read_text(encoding="utf-8"))
        print(f"[INFO] Loaded novel_world_profile from {world_profile_path}")
    else:
        print(f"[WARN] novel_world_profile.json not found at {world_profile_path}, StyleGuide will rely only on keyframes.")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        client = genai.Client()

    model_name = "gemini-3-pro-preview"

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0

    # 1) 生成 Style Guide（参考 world_profile + keyframes）
    style_prompt = build_style_guide_prompt(plan, world_profile=world_profile)

    max_retries = 5
    retry_count = 0
    base_delay = 10

    while retry_count < max_retries:
        try:
            style_resp = client.models.generate_content(
                model=model_name,
                contents=style_prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": TrailerStyleGuide.model_json_schema(),
                },
            )
            break
        except ServerError as e:
            error_msg = str(e)
            if "503" in error_msg or "overloaded" in error_msg.lower():
                retry_count += 1
                if retry_count >= max_retries:
                    sys.stderr.write(
                        f"[ERROR] Max retries ({max_retries}) reached for StyleGuide generation.\n"
                    )
                    raise
                delay = base_delay * (2 ** (retry_count - 1))
                sys.stderr.write(
                    f"[WARN] Model overloaded (503). Retry {retry_count}/{max_retries} after {delay}s...\n"
                )
                time.sleep(delay)
            else:
                raise

    style_raw = getattr(style_resp, "text", None)
    if style_raw is None or not style_raw.strip():
        style_raw = style_resp.candidates[0].content.parts[0].text

    style_guide = TrailerStyleGuide.model_validate_json(style_raw)
    print("[INFO] Generated TrailerStyleGuide")

    if hasattr(style_resp, "usage_metadata") and style_resp.usage_metadata:
        usage = style_resp.usage_metadata
        prompt_tokens = getattr(usage, "prompt_token_count", 0)
        completion_tokens = getattr(usage, "candidates_token_count", 0)
        total = getattr(usage, "total_token_count", 0)
        total_prompt_tokens += prompt_tokens
        total_completion_tokens += completion_tokens
        total_tokens += total
        print(
            f"[TOKEN] StyleGuide generation: {prompt_tokens} prompt + {completion_tokens} completion = {total} total"
        )

    # 2) 用 Style Guide 重写每个 keyframe 的 image_prompt
    new_keyframes: List[Keyframe] = []

    for kf in plan.keyframes:
        print(f"[INFO] Rewriting prompt for {kf.kf_id} (beat {kf.beat_id})")
        rewrite_prompt = build_rewrite_prompt(style_guide, kf)

        retry_count = 0
        content_blocked = False

        while retry_count < max_retries:
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=rewrite_prompt,
                )

                if hasattr(resp, "prompt_feedback") and resp.prompt_feedback:
                    block_reason = getattr(
                        resp.prompt_feedback, "block_reason", None
                    )
                    if block_reason:
                        retry_count += 1
                        if retry_count >= max_retries:
                            sys.stderr.write(
                                f"[WARN] Content blocked for {kf.kf_id} after {max_retries} retries. Reason: {block_reason}\n"
                            )
                            sys.stderr.write(
                                f"[INFO] Keeping original prompt for {kf.kf_id} due to content policy.\n"
                            )
                            if hasattr(resp, "usage_metadata") and resp.usage_metadata:
                                usage = resp.usage_metadata
                                prompt_tokens = getattr(
                                    usage, "prompt_token_count", 0
                                )
                                total_prompt_tokens += prompt_tokens
                                total_tokens += prompt_tokens
                            content_blocked = True
                            break
                        else:
                            delay = 2
                            sys.stderr.write(
                                f"[WARN] Content blocked for {kf.kf_id}. Reason: {block_reason}. "
                                f"Retry {retry_count}/{max_retries} after {delay}s...\n"
                            )
                            time.sleep(delay)
                            continue

                break

            except ServerError as e:
                error_msg = str(e)
                if "503" in error_msg or "overloaded" in error_msg.lower():
                    retry_count += 1
                    if retry_count >= max_retries:
                        sys.stderr.write(
                            f"[ERROR] Max retries ({max_retries}) reached for {kf.kf_id}.\n"
                        )
                        raise
                    delay = base_delay * (2 ** (retry_count - 1))
                    sys.stderr.write(
                        f"[WARN] Model overloaded (503) for {kf.kf_id}. "
                        f"Retry {retry_count}/{max_retries} after {delay}s...\n"
                    )
                    time.sleep(delay)
                else:
                    raise

        if content_blocked:
            new_keyframes.append(kf)
            continue

        new_prompt = getattr(resp, "text", None)
        if new_prompt is None or not new_prompt.strip():
            try:
                if resp.candidates and len(resp.candidates) > 0:
                    parts = resp.candidates[0].content.parts
                    if parts and len(parts) > 0:
                        new_prompt = parts[0].text
                    else:
                        raise ValueError(f"No parts in response for {kf.kf_id}")
                else:
                    raise ValueError(f"No candidates in response for {kf.kf_id}")
            except Exception as e:
                sys.stderr.write(
                    f"[ERROR] Empty or invalid response for {kf.kf_id}: {e}\n"
                )
                sys.stderr.write(
                    f"[INFO] Keeping original prompt for {kf.kf_id}.\n"
                )
                new_keyframes.append(kf)
                continue

        if hasattr(resp, "usage_metadata") and resp.usage_metadata:
            usage = resp.usage_metadata
            prompt_tokens = getattr(usage, "prompt_token_count", 0)
            completion_tokens = getattr(usage, "candidates_token_count", 0)
            total = getattr(usage, "total_token_count", 0)
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens
            total_tokens += total

        # Inherit dialogue_or_text from original keyframe (003), only update image_prompt
        updated = kf.model_copy(update={"image_prompt": new_prompt.strip()})
        new_keyframes.append(updated)

    new_plan = KeyframePlan(
        novel_id=plan.novel_id,
        title=plan.title,
        keyframes=new_keyframes,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        new_plan.model_dump_json(ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[INFO] Styled keyframe plan written to {output_path}")

    print("\n" + "=" * 60)
    print("TOKEN USAGE SUMMARY")
    print("=" * 60)
    print(f"Total Prompt Tokens:     {total_prompt_tokens:,}")
    print(f"Total Completion Tokens: {total_completion_tokens:,}")
    print(f"Total Tokens:            {total_tokens:,}")
    print("=" * 60)


if __name__ == "__main__":
    main()
