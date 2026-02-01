import type { Scene, ExtractScenesResponse, GenerateResponse, RegenerateResponse, BookResponse, DemoGenerateUpdate } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type DemoGenerateCallback = (update: DemoGenerateUpdate) => void;

export async function extractScenes(text: string, numScenes: number = 4): Promise<ExtractScenesResponse> {
  const response = await fetch(`${API_BASE}/api/extract-scenes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, num_scenes: numScenes }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to extract scenes" }));
    throw new Error(error.detail || "Failed to extract scenes");
  }

  return response.json();
}

export async function generateImages(
  scenes: Scene[],
  style: string,
  character: string
): Promise<GenerateResponse> {
  const response = await fetch(`${API_BASE}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenes, style, character }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to generate images" }));
    throw new Error(error.detail || "Failed to generate images");
  }

  return response.json();
}

export async function regenerateImage(
  prompt: string,
  style: string,
  character: string
): Promise<RegenerateResponse> {
  const response = await fetch(`${API_BASE}/api/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, style, character }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to regenerate image" }));
    throw new Error(error.detail || "Failed to regenerate image");
  }

  return response.json();
}

export async function fetchBook(title: string): Promise<BookResponse> {
  const response = await fetch(`${API_BASE}/api/book?title=${encodeURIComponent(title)}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to fetch book" }));
    throw new Error(error.detail || "Failed to fetch book");
  }

  return response.json();
}

export async function generateDemoScene(
  text: string,
  sceneNumber: number,
  onUpdate: DemoGenerateCallback
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/demo-generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, scene_number: sceneNumber }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to generate demo" }));
    throw new Error(error.detail || "Failed to generate demo");
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.trim()) {
        try {
          const update = JSON.parse(line) as DemoGenerateUpdate;
          onUpdate(update);
        } catch (e) {
          console.error("Failed to parse update:", line);
        }
      }
    }
  }
}
