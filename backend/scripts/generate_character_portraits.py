
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ---------- config ----------

BASE_DIR = Path(__file__).resolve().parent

CHAR_PROFILE_PATH = BASE_DIR / "character_base_profiles.json"
WORLD_PROFILE_PATH = BASE_DIR / "novel_world_profile.json"
OUTPUT_DIR = BASE_DIR / "character_portraits_002"

# 根据你实际使用的模型 ID 调整
IMAGE_MODEL_NAME = "gemini-3-pro-image-preview"


# ---------- small utils ----------

def slugify(text: str) -> str:
    """Create a filesystem safe slug from a title or name."""
    text = text.strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text


def load_character_profiles(path: Path) -> List[Dict[str, Any]]:
    """
    读取 character_base_profiles.json
    结构参考:
      {
        "novel_name": "...",     # 如果你已经加了这个字段
        "character_name": "...",
        ...
      }
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]
    return data


def load_world_profile(path: Path) -> Dict[str, Any]:
    """
    Load world profile from novel_world_profile.json.
    Includes global_style field for consistent visual rendering.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def infer_novel_title_from_profiles(profiles: List[Dict[str, Any]]) -> str:
    """
    从 character_base_profiles.json 中推断小说名.

    优先查找字段:
      'novel_name', 'novel_title', 'book_name', 'source_novel'

    如果都没有, 回退为 'Novel'.
    """
    if not profiles:
        return "Novel"

    for p in profiles:
        for key in ["novel_name", "novel_title", "book_name", "source_novel"]:
            val = p.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()

    return "Novel"


# ---------- prompt builder ----------

def build_character_portrait_prompt(
    profile: Dict[str, Any],
    world_profile: Dict[str, Any],
    global_style: str,
) -> str:
    """
    根据 character_base_profile、novel_world_profile 和 GLOBAL_STYLE 生成人物立绘 prompt.
    """
    name = profile.get("character_name", "Unknown character")
    core = profile.get("core_appearance", {}) or {}
    outfit = profile.get("baseline_outfit", {}) or {}
    temperament = profile.get("temperament_baseline", []) or []
    scene_variants = profile.get("scene_variants", []) or []

    # 从 world_profile 中提取背景信息
    era_label = world_profile.get("era_label", "")
    wardrobe_guide = world_profile.get("wardrobe_guide", {})
    color_and_mood = world_profile.get("color_and_mood", "")
    typical_locales = world_profile.get("typical_locales", [])
    visual_motifs = world_profile.get("visual_motifs", [])
    
    # Character core traits
    age_range = core.get("age_range", "")
    body_type = core.get("body_type", "")
    face = core.get("face", "")
    hair = core.get("hair", "")
    
    # Character outfit
    style = outfit.get("style", "")
    materials = outfit.get("materials", "")
    colours = outfit.get("colours", "")
    
    # Temperament
    temperament_desc = ", ".join(temperament[:5]) if temperament else ""

    # 构建人物描述
    char_desc_parts = []
    if age_range:
        char_desc_parts.append(f"Age: {age_range}")
    if body_type:
        char_desc_parts.append(f"Build: {body_type}")
    if face:
        char_desc_parts.append(f"Face: {face}")
    if hair:
        char_desc_parts.append(f"Hair: {hair}")
    
    char_physical = "; ".join(char_desc_parts) if char_desc_parts else "a notable character"

    # 构建服装描述，参考wardrobe_guide和character的baseline_outfit
    outfit_parts = []
    if style:
        outfit_parts.append(style)
    if materials:
        outfit_parts.append(f"made of {materials}")
    if colours:
        outfit_parts.append(f"in {colours}")
    
    # 根据角色类型从wardrobe_guide中补充细节
    # 假设可以从temperament或outfit style推断角色类型
    wardrobe_hint = ""
    if wardrobe_guide:
        # 简单启发式：如果是女性角色且提到elegant/layered/robes，使用noblewoman指南
        if "elegant" in style.lower() or "silk" in materials.lower() or "robe" in style.lower():
            wardrobe_hint = wardrobe_guide.get("noblewoman", "")
        # 如果提到armor/military，使用young_general指南
        elif "armor" in style.lower() or "military" in style.lower():
            wardrobe_hint = wardrobe_guide.get("young_general", "")
        # 如果提到official/purple/gold，使用imperial_officials指南
        elif "official" in style.lower() or "purple" in colours.lower():
            wardrobe_hint = wardrobe_guide.get("imperial_officials", "")
    
    outfit_desc = ", ".join(outfit_parts) if outfit_parts else "traditional attire"
    if wardrobe_hint:
        outfit_desc += f". {wardrobe_hint[:200]}"  # 限制长度避免prompt过长

    # 选择适合的背景场景
    background_locale = "a subtle courtyard setting"
    if typical_locales:
        # 优先选择府邸或庭院场景
        for loc in typical_locales:
            if "Mansion" in loc or "courtyard" in loc.lower():
                background_locale = f"{loc}, subtle and timeless"
                break

    # 添加visual motifs作为氛围细节
    motif_details = ""
    if visual_motifs and len(visual_motifs) > 0:
        # 选择前3个最相关的motifs
        selected_motifs = [m for m in visual_motifs[:3] if "(" in m]  # 优先选择有说明的
        if not selected_motifs:
            selected_motifs = visual_motifs[:3]
        motif_details = f"Visual motifs to subtly incorporate: {', '.join(selected_motifs)}."

    prompt = f"""{global_style.strip()}

Full body portrait of {name}, a main character from "{world_profile.get('novel_name', 'the novel')}".

Era & Setting: {era_label}. {color_and_mood}

Character Physical Traits: {char_physical}

Temperament & Aura: {temperament_desc if temperament_desc else 'dignified and composed'}

Attire: {outfit_desc}

Pose & Expression: Standing in a neutral, timeless pose. Calm and composed expression, facing the camera. Clear view of face and full outfit.

Background: {background_locale}. Clean, uncluttered background that emphasizes the character. {motif_details}

Lighting: Dramatic yet natural lighting that highlights the character's features and attire, consistent with the mood of the novel.

Technical: High-fidelity character concept art, 16:9 aspect ratio, detailed textures on fabric and materials.
"""

    return prompt



# ---------- image generation ----------

def generate_image_and_save(
    client: genai.Client,
    model_name: str,
    prompt: str,
    output_path: Path,
) -> None:

    response = client.models.generate_content(
        model=model_name,
        contents=[prompt],
        config=types.GenerateContentConfig(
            image_config=types.ImageConfig(
            )
        ),
    )

    # 从 response.parts 中提取图像并保存
    for part in response.parts:
        if part.inline_data is not None:
            img = part.as_image()  # 转成 Pillow Image
            img.save(output_path)
            return
    
    raise RuntimeError("No image found in response")


def generate_character_portraits(
    char_profile_path: Path,
    world_profile_path: Path,
    output_dir: Path,
    image_model_name: str = IMAGE_MODEL_NAME,
):
    load_dotenv()
    client = genai.Client()

    output_dir.mkdir(parents=True, exist_ok=True)

    profiles = load_character_profiles(char_profile_path)
    if not profiles:
        raise ValueError(f"No profiles found in {char_profile_path}")

    world_profile = load_world_profile(world_profile_path)
    novel_title = world_profile.get("novel_name") or infer_novel_title_from_profiles(profiles)
    novel_slug = slugify(novel_title)

    global_style = world_profile.get("global_style", "")
    if not global_style:
        print("[WARN] No 'global_style' field found in novel_world_profile.json, using default")
        global_style = "Cinematic digital illustration with detailed textures and dramatic lighting."

    print(f"[INFO] Novel title: {novel_title}")
    print(f"[INFO] Loaded {len(profiles)} character profiles")
    print(f"[INFO] Loaded world profile from {world_profile_path}")
    print(f"[INFO] Using global_style from novel_world_profile.json")

    for profile in profiles:
        name = profile.get("character_name", "Unknown")
        print(f"[INFO] Generating portrait for {name}...")

        prompt = build_character_portrait_prompt(
            profile=profile,
            world_profile=world_profile,
            global_style=global_style,
        )

        filename = f"{novel_slug}_{slugify(name)}.png"
        out_path = output_dir / filename

        generate_image_and_save(
            client=client,
            model_name=image_model_name,
            prompt=prompt,
            output_path=out_path,
        )

        print(f"[INFO] Saved portrait to {out_path}")


def main():
    generate_character_portraits(
        char_profile_path=CHAR_PROFILE_PATH,
        world_profile_path=WORLD_PROFILE_PATH,
        output_dir=OUTPUT_DIR,
        image_model_name=IMAGE_MODEL_NAME,
    )


if __name__ == "__main__":
    main()
