import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Optional

from google import genai
from google.genai.errors import ServerError
from pydantic import BaseModel, Field
from dotenv import load_dotenv


# ---------- 默认文件路径配置 ----------
DEFAULT_INPUT_PATH = "/Users/lee/Documents/Career/AI/Readgates/novel2trailer/Ghost_Blows_Out_the_Light_II/novel.json"
DEFAULT_OUTPUT_PATH = "/Users/lee/Documents/Career/AI/Readgates/novel2trailer/Ghost_Blows_Out_the_Light_II/novel_scenes.json"


# ---------- Pydantic 数据结构, 用于 structured output ----------

class Scene(BaseModel):
    scene_id: str = Field(
        description="Scene index within this chapter, starting from '1', e.g. '1','2','3'..."
    )
    chapter: str = Field(
        description="Chapter id or title this scene belongs to, e.g. 'Chapter 1'"
    )
    brief: str = Field(
        description="One or two sentences summarizing what happens in this scene"
    )
    original_text: str = Field(
        description="The original text content of this scene, maximal 5 sentences extracted from original chapter"
    )
    characters: List[str] = Field(
        description="List of important characters appearing in this scene"
    )
    emotion_tags: List[str] = Field(
        description="List of emotion tags for this scene, e.g. ['angst','romance','suspense','warm','tragic']"
    )
    function: str = Field(
        description=(
            "the narrative function of this scene in the overall story,and also the summary of this scene"
        )
    )


class ChapterScenes(BaseModel):
    chapter_id: str
    chapter_title: str
    volume_name: Optional[str] = None
    scenes: List[Scene]


class NovelScenes(BaseModel):
    novel_id: str
    title: Optional[str] = None
    author: Optional[str] = None
    language: Optional[str] = None
    metadata: Optional[dict] = None
    chapters: List[ChapterScenes]


# ---------- Prompt 构造 ----------

def build_prompt_for_chapter(
    novel_title: str,
    chapter_id: str,
    chapter_title: str,
    volume_name: str,
    chapter_text: str,
    language: str,
    novel_summary:str,
    ) -> str:


    prompt = f"""
    You are a novel structure analysis assistant， good at improtant or emotional scenes extraction from novels.
    You will receive the FULL TEXT of ONE chapter of an English web novel, this web novel is about "{novel_summary}".

    Your task:
    - extract all major plot beats of the chapter, especially emotional turns and key decisions which impact the overall story arc.
    - For each scene, fill in the required fields of the JSON schema described below.
    - You MUST strictly follow the JSON schema. Do NOT add extra top-level fields.

    [Output JSON object: ChapterScenes]
    You MUST output a single JSON object with fields:
    - chapter_id: the id of this chapter, MUST be exactly: "{chapter_id}"
    - chapter_title: the title of this chapter, MUST be exactly: "{chapter_title}"
    - volume_name: the volume name, MUST be exactly: "{volume_name}"
    - scenes: an array of Scene objects. Each Scene has:
    - scene_id: string index within this chapter, starting from "1", then "2","3",...
    - chapter: a short identifier for this chapter, you SHOULD use "{chapter_id}"
    - brief: summarizing what happens in this scene (concise but concrete)
    - original_text: the original text content of this scene, 5 sentences extracted from original chapter
    - characters: list of important characters appearing in this scene (use names as in the text)
    - emotion_tags: list of emotion or tone tags, e.g. ["angst","romance","suspense","warm","tragic","tension","relief"]
    - function: the narrative function of this scene in the overall story,and also the summary of this scene,
        for example: "first_meeting","foreshadowing","reveal_truth","backstory",
                    "internal_conflict","external_conflict","breakup","reconciliation",
                    "climax","turning_point","slice_of_life"


    [Novel info]
    - novel_title: {novel_title}
    - chapter_id: {chapter_id}
    - chapter_title: {chapter_title}
    - volume_name: {volume_name}
    - language: {language}

    [CHAPTER TEXT START]
    {chapter_text}
    [CHAPTER TEXT END]
    """
    return prompt


# ---------- 调用 Gemini: 对单章节抽取场景 ----------

def extract_scenes_for_chapter(
    client: "genai.Client",
    model_name: str,
    novel_title: str,
    chapter_id: str,
    chapter_title: str,
    volume_name: str,
    chapter_text: str,
    language: str,
    novel_summary: str,
) -> ChapterScenes:
    """
    调用 Gemini, 对单个章节做场景抽取, 返回 ChapterScenes 对象.
    """

    prompt = build_prompt_for_chapter(
        novel_title=novel_title,
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        volume_name=volume_name,
        chapter_text=chapter_text,
        language=language,
        novel_summary=novel_summary,
    )

    # 重试逻辑处理503服务过载错误
    max_retries = 5
    retry_count = 0
    base_delay = 10  # 基础延迟10秒
    
    while retry_count < max_retries:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": ChapterScenes.model_json_schema(),
                },
            )
            break  # 成功则跳出循环
            
        except ServerError as e:
            # 检查错误信息中是否包含503或overloaded
            error_msg = str(e)
            if '503' in error_msg or 'overloaded' in error_msg.lower():
                retry_count += 1
                if retry_count >= max_retries:
                    sys.stderr.write(
                        f"[ERROR] Max retries ({max_retries}) reached for chapter {chapter_id}. "
                        f"Model overloaded.\n"
                    )
                    raise
                
                # 指数退避延迟
                delay = base_delay * (2 ** (retry_count - 1))
                sys.stderr.write(
                    f"[WARN] Model overloaded (503) for chapter {chapter_id}. "
                    f"Retry {retry_count}/{max_retries} after {delay}s...\n"
                )
                time.sleep(delay)
            else:
                # 其他ServerError直接抛出
                raise

    # 检查是否被内容安全策略拦截
    if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
        block_reason = getattr(response.prompt_feedback, 'block_reason', None)
        if block_reason:
            sys.stderr.write(
                f"[ERROR] Content blocked for chapter {chapter_id}. Reason: {block_reason}\n"
            )
            sys.stderr.write(f"[INFO] Skipping chapter {chapter_id} due to content policy.\n")
            # 返回一个空的 ChapterScenes
            return ChapterScenes(
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                volume_name=volume_name,
                scenes=[]
            )

    # google-genai 通常在 response.text 里给出 JSON 字符串
    raw_text = getattr(response, "text", None)
    if raw_text is None or not raw_text.strip():
        # 兜底: 有些情况内容在 candidates 里
        try:
            if response.candidates and len(response.candidates) > 0:
                raw_text = response.candidates[0].content.parts[0].text
            else:
                raise ValueError("No candidates in response")
        except Exception:
            sys.stderr.write(
                f"[ERROR] Empty response for chapter {chapter_id}. Raw response: {response}\n"
            )
            raise

    try:
        chapter_scenes = ChapterScenes.model_validate_json(raw_text)
    except Exception as e:
        sys.stderr.write(
            f"[ERROR] Failed to parse JSON for chapter {chapter_id}: {e}\n"
        )
        sys.stderr.write("Raw model response:\n")
        sys.stderr.write(raw_text + "\n")
        raise

    return chapter_scenes


# ---------- 主流程: 读整本小说, 按 volume/chapter 抽取, 汇总输出 ----------

def process_novel(
    input_path: Path,
    output_path: Path,
    model_name: str = "gemini-3-pro-preview",
) -> None:
    

    # 1. 读取整本小说 JSON
    with input_path.open("r", encoding="utf-8") as f:
        novel_data = json.load(f)

    # 你的 JSON 里没有 novel_id, 用 bookCode 或 name 作为 id
    novel_id = novel_data.get("bookCode") or novel_data.get("name") or "unknown_novel"
    novel_title = novel_data.get("name", "")
    author = novel_data.get("author")
    language = novel_data.get("language", "en")
    novel_summary = novel_data.get("summary", "")
    volumes = novel_data.get("volumes", [])

    # 顺便把原始 metadata 保留到输出里
    metadata = {
        k: v
        for k, v in novel_data.items()
        if k not in ["volumes"]  # volumes 单独处理
    }

    if not volumes:
        raise ValueError("Input JSON 中没有 'volumes' 字段或内容为空.")

    # 2. 初始化 Gemini client (从 GEMINI_API_KEY 读取密钥)
    load_dotenv()
    client = genai.Client()

    chapter_summaries: List[ChapterScenes] = []
    chapter_counter = 0  # 用来生成全局 chapter_id

    # 3. 遍历每一个 volume 和其中的 chapter
    for vol_idx, vol in enumerate(volumes, start=1):
        volume_name = vol.get("name") or f"Volume {vol_idx}"
        chapters = vol.get("chapters") or []

        if not chapters:
            continue

        for ch_idx, ch in enumerate(chapters, start=1):
            chapter_counter += 1
            # 统一生成一个 global chapter_id, 方便后续引用
            chapter_id = f"v{vol_idx:02d}_ch{ch_idx:03d}"
            chapter_title = ch.get("name") or f"Chapter {chapter_counter}"
            chapter_text = ch.get("content") or ""

            print(f"[INFO] Processing {chapter_id} - {chapter_title} (volume: {volume_name}) ...")

            if not chapter_text.strip():
                print(f"[WARN] Chapter {chapter_id} has empty content, skipping.")
                empty_cs = ChapterScenes(
                    chapter_id=chapter_id,
                    chapter_title=chapter_title,
                    volume_name=volume_name,
                    scenes=[],
                )
                chapter_summaries.append(empty_cs)
                continue

            cs = extract_scenes_for_chapter(
                client=client,
                model_name=model_name,
                novel_title=novel_title,
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                volume_name=volume_name,
                chapter_text=chapter_text,
                language=language,
                novel_summary=novel_summary,
            )

            # 确保 volume_name 写进去 (即使模型没填)
            cs.volume_name = volume_name
            chapter_summaries.append(cs)

    # 4. 汇总为 NovelScenes, 写出到输出 JSON
    novel_scenes = NovelScenes(
        novel_id=novel_id,
        title=novel_title,
        author=author,
        language=language,
        metadata=metadata,
        chapters=chapter_summaries,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(
            json.loads(novel_scenes.model_dump_json(ensure_ascii=False)),
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"[INFO] Done. Scene index written to: {output_path}")


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(
        description="Extract scene index from a whole novel (with volumes/chapters) JSON using Gemini."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=DEFAULT_INPUT_PATH,
        help="Input novel JSON file path.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=DEFAULT_OUTPUT_PATH,
        help="Output scene index JSON file path.",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default="gemini-3-pro-preview",
        help="Gemini model name (default: gemini-3-pro-preview).",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    process_novel(
        input_path=input_path,
        output_path=output_path,
        model_name=args.model,
    )


if __name__ == "__main__":
    main()
