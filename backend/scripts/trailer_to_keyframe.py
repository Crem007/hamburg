from typing import List, Literal, Optional, Dict
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pathlib import Path
import json
from google import genai


ShotType = Literal[
    "ELS", "LS", "MLS", "MS", "MCU", "CU", "ECU",
    "Insert", "Low", "High", "BirdsEye", "WormsEye"
]


class Keyframe(BaseModel):
    kf_id: str = Field(description="Global keyframe id, e.g. 'KF_B1_01'")
    beat_id: str = Field(description="Id of the beat, e.g. 'B1'")
    order_in_beat: int = Field(description="1 based index within this beat")
    suggested_duration_sec: float = Field(description="How long this frame roughly holds on screen")

    shot_type: ShotType = Field(description="Shot type for cinematography")
    camera_angle: str = Field(description="Camera height and angle, e.g. 'slightly high, 3 meters away'")
    composition: str = Field(description="Framing and spatial arrangement description")
    action: str = Field(description="What is visibly happening in this frame, need describe what the characters are doing")
    emotion_tags: List[str] = Field(description="Emotional tags for this moment")

    characters: List[str] = Field(
        description="List of main character names visible or referenced in this keyframe. Inherited from beat."
    )
    story_grounding: dict = Field(
        description="Reference to source_scenes and relevant novel lines, for traceability"
    )
    dialogue_or_text: Optional[str] = Field(
        description="MUST generate One short line of dialogue or on screen text for this frame"
    )

    image_prompt: str = Field(
        description=(
            "Content only prompt for an image model. "
            "Describe who is in the scene, where, doing what, camera distance and angle, "
            "time of day, physical lighting direction and environment details. "
            "Do NOT include any rendering or art style words such as 'oil painting', "
            "'photorealistic', 'anime', 'concept art', 'cinematic lighting', '4k', '8k', "
            "'HDR', 'digital art', 'illustration' etc. "
            "A later step will add global style."
        )
    )


class BeatKeyframes(BaseModel):
    beat_id: str
    role: str
    keyframes: List[Keyframe]


class KeyframePlan(BaseModel):
    novel_id: str
    title: str
    keyframes: List[Keyframe]


def build_keyframe_prompt_for_beat(
    beat: dict,
    scenes_for_beat: list,
    novel_id: str,
    title: str,
) -> str:
    """
    为单个 beat 构建 keyframe 生成 prompt, 包含完整的原文摘录.
    这里的 image_prompt 只允许写"内容", 禁止写"风格".
    """
    scenes_text_blocks = []
    for s in scenes_for_beat:
        sid = s.get("scene_id", "")
        chap = s.get("chapter", "")
        scene_uid = f"{chap}_s{sid}" if chap and sid else sid

        brief = s.get("brief", "")
        chars = ", ".join(s.get("characters", []))
        emos = ", ".join(s.get("emotion_tags", []))
        func = s.get("function", "")
        original_text = s.get("original_text", "")

        block = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scene: {scene_uid}
Chapter: {chap}
Brief: {brief}
Characters: {chars}
Emotion Tags: {emos}
Function: {func}

ORIGINAL TEXT EXCERPT:
{original_text if original_text else "[No original text available]"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        scenes_text_blocks.append(block)

    scenes_text = "\n".join(scenes_text_blocks)

    km = beat.get("key_moments") or []
    if isinstance(km, str):
        km = [km]
    key_moments_str = "\n- ".join(km)

    dl = beat.get("dialogue_or_text") or []
    if isinstance(dl, str):
        dl = [dl]
    dialogue_str = "\n- ".join(dl)

    prompt = f"""
You are a senior book trailer storyboard artist and cinematographer designing 2-3 keyframes for ONE trailer beat.
Your work will generate high-quality still images with an AI image model.
In this step you only define the CONTENT of the frames, not the visual style.

====================
NOVEL CONTEXT
====================
- novel_id: {novel_id}
- title: {title}

====================
FOCAL BEAT (FROM TRAILER SCRIPT)
====================
- beat_id: {beat.get("beat_id")}
- role: {beat.get("role")} (hook/conflict/escalation/cliffhanger)
- duration_sec: {beat.get("duration_sec")}
- logline: {beat.get("logline")}
- visual_idea: {beat.get("visual_idea")}

Key moments to visualize:
- {key_moments_str}

Dialogue or on screen text candidates:
- {dialogue_str}

====================
SOURCE SCENES (FROM NOVEL)
====================
CRITICAL: Ground all visual choices in the ORIGINAL TEXT EXCERPT below.
Use specific details, descriptions, and moments from the text.
You may compress or combine details for cinematic effect, but stay faithful to the source.

{scenes_text}

====================
YOUR TASK
====================
For this beat, design 2-3 keyframes that:
- Visually express the beat's role and logline.
- Are clearly grounded in the ORIGINAL TEXT above with specific details.
- Use varied shot types, angles, and distances.
- Provide concrete detail: setting, physical lighting direction, costumes, props, expressions.
- Each keyframe's image and dialogue_or_text must work together to tell a complete story moment.

For EACH keyframe, specify:

TECHNICAL:
- shot_type: one of [ELS, LS, MLS, MS, MCU, CU, ECU, Insert, Low, High, BirdsEye, WormsEye].
- camera_angle: physical viewpoint (height, distance, direction).
- composition: spatial arrangement of characters and elements in frame.
- action: what is visibly happening (cinematic language), what the characters are doing.
- emotion_tags: 2-5 emotional tags.

STORY CONNECTION:
- story_grounding: which scene id(s) this draws from and 1-2 key phrases from the original text.
- dialogue_or_text: REQUIRED. One short, powerful line of text for this frame that works WITH the image to tell the story. You may choose either:
  * Third-person narrative voice (e.g., "She returns to the past", "A promise is made", "The army marches to doom")
  * First-person protagonist voice as inner monologue or voiceover (e.g., "I won't let them die again", "This time, I'll save you")
  Choose the voice that best serves the emotional impact and narrative clarity of THIS specific moment. Keep it concise and evocative (5-12 words maximum). The text and image together should convey a complete story beat.

IMAGE PROMPT (CONTENT ONLY):
- image_prompt: a single, self-contained prompt string for an image AI model that describes only:
  - who is present, their age, clothing, posture, expression
  - where they are (environment, architecture, interior or exterior)
  - what they are doing
  - camera distance and angle
  - time of day and physical lighting direction (for example morning sun from the left, torchlight from behind)
- Do NOT include any rendering or art style words.
  Do NOT mention anime, oil painting, sketch, photorealistic, cinematic lighting, concept art,
  digital art, illustration, 3d, 4k, 8k, HDR, film still, or similar.
  A later step will add the global visual style.

====================
OUTPUT FORMAT
====================
Output a single valid JSON object of type BeatKeyframes:
{{
  "beat_id": "{beat.get('beat_id')}",
  "role": "{beat.get('role')}",
  "keyframes": [
    {{
      "kf_id": "KF_{beat.get('beat_id')}_01",
      "beat_id": "{beat.get('beat_id')}",
      "order_in_beat": 1,
      "suggested_duration_sec": <float>,
      "shot_type": "<type>",
      "camera_angle": "<description>",
      "composition": "<description>",
      "action": "<description>",
      "emotion_tags": ["tag1", "tag2"],
      "story_grounding": {{"scene_ids": ["{beat.get('beat_id')}"], "novel_lines": ["..."]}},
      "dialogue_or_text": "<required: powerful narrative or protagonist voice, 5-12 words, complements the image>",
      "image_prompt": "<content only image prompt, no style words>"
    }}
  ]
}}
No comments, no trailing commas, valid JSON only.
"""
    return prompt


def index_scenes_by_id(novel_scenes_output: dict) -> Dict[str, dict]:
    """
    把 NovelScenes 里的所有 scene flatten 成 scene_id -> scene dict.
    同时提供 v01_ch001_s4 这种复合 ID 以匹配 trailer_script.json 的 source_scenes.
    """
    mapping: Dict[str, dict] = {}
    for ch in novel_scenes_output.get("chapters", []):
        chap_id = ch.get("chapter_id", "")
        for s in ch.get("scenes", []):
            sid = s.get("scene_id")
            if not sid:
                continue

            if chap_id:
                compound = f"{chap_id}_s{sid}"  # 例如 v01_ch001_s4
                mapping[compound] = s

            mapping[sid] = s

    return mapping


def generate_keyframes_for_trailer(
    scenes_path: Path,
    trailer_script_path: Path,
    output_path: Path,
    model_name: str = "gemini-3-pro-preview",
):
    novel_scenes_output = json.loads(scenes_path.read_text(encoding="utf-8"))
    trailer_script = json.loads(trailer_script_path.read_text(encoding="utf-8"))

    scene_index = index_scenes_by_id(novel_scenes_output)

    novel_id = trailer_script.get("novel_id") or novel_scenes_output.get("novel_id", "unknown_novel")
    title = trailer_script.get("title") or novel_scenes_output.get("title", "unknown_title")

    beats: List[dict] = trailer_script.get("beats", [])

    client = genai.Client()

    all_keyframes: List[Keyframe] = []

    for beat in beats:
        beat_id = beat.get("beat_id")
        role = beat.get("role")
        print(f"[INFO] Generating keyframes for beat {beat_id} ({role}) ...")

        source_ids = beat.get("source_scenes", [])
        scenes_for_beat = [scene_index[sid] for sid in source_ids if sid in scene_index]

        if not scenes_for_beat:
            print(f"[WARN] No scenes found for beat {beat_id}, skipping.")
            continue

        prompt = build_keyframe_prompt_for_beat(
            beat=beat,
            scenes_for_beat=scenes_for_beat,
            novel_id=novel_id,
            title=title,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": BeatKeyframes.model_json_schema(),
            },
        )

        raw = getattr(response, "text", None)
        if raw is None or not raw.strip():
            raw = response.candidates[0].content.parts[0].text

        beat_kf = BeatKeyframes.model_validate_json(raw)

        # 从 beat 继承 characters 字段，减少模型计算量
        beat_characters = beat.get("characters", [])
        for kf in beat_kf.keyframes:
            kf.characters = beat_characters

        all_keyframes.extend(beat_kf.keyframes)

    plan = KeyframePlan(
        novel_id=novel_id,
        title=title,
        keyframes=all_keyframes,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(
            json.loads(plan.model_dump_json(ensure_ascii=False)),
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"[INFO] Keyframe plan written to {output_path}")


def main():
    load_dotenv()
    scenes_path = Path("/Users/lee/Documents/Career/AI/Readgates/novel2trailer/Ghost_Blows_Out_the_Light_II/novel_scenes.json")
    trailer_script_path = Path("/Users/lee/Documents/Career/AI/Readgates/novel2trailer/Ghost_Blows_Out_the_Light_II/trailer_script.json")
    output_path = Path("/Users/lee/Documents/Career/AI/Readgates/novel2trailer/Ghost_Blows_Out_the_Light_II/keyframe_plan.json")

    generate_keyframes_for_trailer(
        scenes_path=scenes_path,
        trailer_script_path=trailer_script_path,
        output_path=output_path,
        model_name="gemini-3-pro-preview",
    )


if __name__ == "__main__":
    main()
