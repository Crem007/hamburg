import os
import json
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image


# ===== 统一文字叠加样式规范 =====
TEXT_OVERLAY_STYLE = (
    "Text overlay style rules (when text is present): "
    "Use elegant serif font in white or soft cream color with a subtle dark shadow (2-3px offset) for legibility. "
    "Position text in the lower third of the frame, horizontally centered. "
    "Font size should be prominent but not overwhelming (approximately 8-10% of frame height). "
    "Add a soft semi-transparent dark gradient vignette behind the text area (spanning 15-20% of frame height) "
    "to ensure text remains readable against any background. "
    "The text should feel like a natural part of the cinematic composition, "
    "matching the historical Chinese aesthetic with dignified, classical typography. "
    "Keep consistent character spacing and line height across all frames."
)


def load_world_profile(world_profile_path: Path) -> dict:
    """加载 novel_world_profile.json，获取 global_style 等信息"""
    return json.loads(world_profile_path.read_text(encoding="utf-8"))


def load_keyframes(keyframe_plan_path: Path):
    data = json.loads(keyframe_plan_path.read_text(encoding="utf-8"))
    keyframes = data.get("keyframes", [])
    if not isinstance(keyframes, list):
        raise ValueError("keyframe_plan.json 中的 'keyframes' 字段不是列表")
    title = data.get("title", "Unknown Novel")
    return keyframes, title


def find_character_portraits(characters: List[str], novel_name: str, portraits_dir: Path) -> List[Path]:
    """
    根据角色名列表查找对应的立绘文件
    立绘文件命名格式: {Novel_Name}_{Character_Name}.png
    例如: Rivers_and_Mountains_as_My_Pillow_Chu_Yu.png
    """
    portrait_files = []
    # 将小说名转换为文件名格式（空格替换为下划线）
    novel_name_formatted = novel_name.replace(" ", "_")
    
    for char_name in characters:
        # 将角色名转换为文件名格式（空格替换为下划线）
        char_name_formatted = char_name.replace(" ", "_")
        portrait_filename = f"{novel_name_formatted}_{char_name_formatted}.png"
        portrait_path = portraits_dir / portrait_filename
        
        if portrait_path.exists():
            portrait_files.append(portrait_path)
            print(f"[INFO] Found portrait for {char_name}: {portrait_filename}")
        else:
            print(f"[WARN] Portrait not found for {char_name}: {portrait_filename}")
    
    return portrait_files


def build_image_prompt(kf: dict, global_style: str) -> str:
    """
    把 global_style 和 image_prompt 拼成最终给模型的文本 prompt
    如果有 dialogue_or_text，要求在图片中作为文字叠加层显示
    """
    base_prompt = kf.get("image_prompt", "").strip()
    if not base_prompt:
        raise ValueError(f"Keyframe {kf.get('kf_id')} 缺少 image_prompt")

    # 检查是否有 dialogue_or_text
    dialogue_text = kf.get("dialogue_or_text", "").strip()
    
    # 最终 prompt: 全局风格 + 原本的 image_prompt
    prompt = f"{global_style} {base_prompt}"
    
    # 如果有对白或文字，添加统一的文字叠加样式和具体文本内容
    if dialogue_text:
        prompt += f"\n\n{TEXT_OVERLAY_STYLE}\n\nText to display: \"{dialogue_text}\""

    return prompt


def generate_image_for_prompt(client, model_name: str, prompt: str, aspect_ratio: str, portrait_images: Optional[List[Image.Image]] = None):

    # 构建contents: 如果有立绘，先传立绘图片，再传文本prompt
    contents = []
    
    if portrait_images:
        for img in portrait_images:
            contents.append(img)
        # 添加说明文字，强调只参考人物特征
        contents.append(
            "The images above are character portrait references. "
            "ONLY use them as reference for the character's facial features, hairstyle, clothing style, and physical appearance. "
            "DO NOT copy the portrait's composition, background, pose, or framing. "
            "Generate a completely new scene as described in the prompt below, "
            "while keeping the character's appearance consistent with the portrait reference:"
        )
    
    contents.append(prompt)
    
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
            )
        ),
    )

    images = []
    if response.parts:
        for part in response.parts:
            if part.inline_data is not None:
                img = part.as_image()  # 转成 Pillow Image
                images.append(img)

    return images, response


def main():
    load_dotenv()

    # 你自己的路径, 按需改
    base_dir = Path(__file__).resolve().parent
    
    world_profile_path = base_dir / "novel_world_profile.json"
    keyframe_plan_path = base_dir / "keyframe_plan_styled.json"
    portraits_dir = base_dir / "character_portraits_002"
    
    if not portraits_dir.exists():
        print(f"[WARN] Character portraits directory not found: {portraits_dir}")
        print(f"[WARN] Will generate keyframes without character portrait references")
    
    output_dir = base_dir / "keyframe_images"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载 world profile 获取 global_style
    world_profile = load_world_profile(world_profile_path)
    global_style = world_profile.get("global_style", "")
    if not global_style:
        print("[WARN] No 'global_style' field found in novel_world_profile.json, using default")
        global_style = "Cinematic digital illustration with detailed textures and dramatic lighting."
    
    print(f"[INFO] Loaded global_style from {world_profile_path}")

    # 初始化 Gemini client
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        client = genai.Client()

    model_name = "gemini-3-pro-image-preview"

    # Token计数器和费用跟踪
    # Gemini 3 Pro Image Preview 定价: $0.002 per image (截至2025年)
    total_prompt_tokens = 0
    total_images_generated = 0
    price_per_image = 0.002  # USD

    keyframes, novel_title = load_keyframes(keyframe_plan_path)
    print(f"[INFO] Novel: {novel_title}")
    print(f"[INFO] Loaded {len(keyframes)} keyframes from {keyframe_plan_path}")

    for kf in keyframes:
        kf_id = kf.get("kf_id", "unknown_kf")
        beat_id = kf.get("beat_id", "unknown_beat")
        
        # 检查图片是否已存在
        out_path = output_dir / f"{kf_id}.png"
        if out_path.exists():
            print(f"[INFO] Image already exists for {kf_id}, skipping generation")
            continue
        
        print(f"[INFO] Generating image for {kf_id} (beat {beat_id}) ...")

        try:
            prompt = build_image_prompt(kf, global_style)
        except ValueError as e:
            print(f"[WARN] Skip {kf_id}: {e}")
            continue

        # 获取该keyframe中的角色列表
        characters = kf.get("characters", [])
        print(f"[INFO] Characters in {kf_id}: {characters}")
        
        # 加载角色立绘
        portrait_images = []
        if characters and portraits_dir.exists():
            print(f"[INFO] Loading portraits for: {characters}")
            portrait_paths = find_character_portraits(characters, novel_title, portraits_dir)
            for portrait_path in portrait_paths:
                try:
                    img = Image.open(portrait_path)
                    portrait_images.append(img)
                except Exception as e:
                    print(f"[ERROR] Failed to load portrait {portrait_path}: {e}")
        elif characters and not portraits_dir.exists():
            print(f"[INFO] Skipping portrait loading - directory not found")
        
        if portrait_images:
            print(f"[INFO] Using {len(portrait_images)} character portrait(s) as reference")

        # 可选: 打印一下 prompt 看看有没有你想要的镜头语言
        print(f"\n=== PROMPT FOR {kf_id} ===\n{prompt}\n")

        try:
            images, response = generate_image_for_prompt(
                client=client,
                model_name=model_name,
                prompt=prompt,
                aspect_ratio="9:16",
                portrait_images=portrait_images if portrait_images else None,
            )
        except Exception as e:
            print(f"[ERROR] Gemini image generation failed for {kf_id}: {e}")
            continue

        if not images:
            print(f"[WARN] No image returned for {kf_id}")
            continue

        # 统计 token 使用
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            prompt_tokens = getattr(usage, 'prompt_token_count', 0)
            total_prompt_tokens += prompt_tokens
        
        total_images_generated += 1

        img = images[0]
        out_path = output_dir / f"{kf_id}.png"
        img.save(out_path)
        print(f"[INFO] Saved image for {kf_id} -> {out_path}")


    # 打印 token 统计和费用
    total_cost = total_images_generated * price_per_image
    print("\n" + "="*60)
    print("TOKEN USAGE & COST SUMMARY")
    print("="*60)
    print(f"Total Prompt Tokens:     {total_prompt_tokens:,}")
    print(f"Total Images Generated:  {total_images_generated}")
    print(f"Price per Image:         ${price_per_image:.4f}")
    print(f"Total Cost (USD):        ${total_cost:.4f}")
    print("="*60)



if __name__ == "__main__":
    main()
