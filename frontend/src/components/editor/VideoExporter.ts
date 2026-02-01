/**
 * Video exporter using mediabunny for MP4 encoding.
 * Extracted from viral-launch-video-main.
 */

import {
  ALL_FORMATS,
  AudioBufferSink,
  AudioBufferSource,
  BufferTarget,
  CanvasSource,
  Input,
  Mp4OutputFormat,
  Output,
  QUALITY_HIGH,
  UrlSource,
} from "mediabunny";
import type { PixiEditor } from "./PixiEditor";
import type { TimelineItemVideo } from "./types";

export class VideoExporter {
  public static async export(
    editor: PixiEditor,
    options: {
      fps?: number;
      duration?: number;
      onProgress?: (progress: number) => void;
    } = {}
  ): Promise<Uint8Array> {
    const fps = options.fps || 30;
    const onProgress = options.onProgress || (() => {});
    const timeline = editor.getTimeline();
    const app = editor.getApp();

    // 1. Calculate total duration
    let totalDuration = 0;
    for (const item of timeline.items) {
      const end = item.startTime + item.duration;
      if (end > totalDuration) totalDuration = end;
    }

    if (options.duration && options.duration < totalDuration) {
      totalDuration = options.duration;
    }

    if (totalDuration === 0) {
      throw new Error("Timeline is empty or has 0 duration");
    }

    // 2. Setup Output
    const output = new Output({
      format: new Mp4OutputFormat(),
      target: new BufferTarget(),
    });

    // 3. Configure Audio Track
    const videoItems = timeline.items
      .filter((i) => i.type === "video")
      .sort((a, b) => a.startTime - b.startTime) as TimelineItemVideo[];

    let audioSource: AudioBufferSource | null = null;

    if (videoItems.length > 0) {
      audioSource = new AudioBufferSource({
        codec: "aac",
        bitrate: QUALITY_HIGH,
      });
      output.addAudioTrack(audioSource);
    }

    // 4. Configure Video Track
    const canvas = app.canvas as HTMLCanvasElement;

    // Ensure even dimensions for AVC
    const width = app.renderer.width;
    const height = app.renderer.height;

    if (width % 2 !== 0 || height % 2 !== 0) {
      const newWidth = width % 2 !== 0 ? width - 1 : width;
      const newHeight = height % 2 !== 0 ? height - 1 : height;
      app.renderer.resize(newWidth, newHeight);
    }

    const videoSource = new CanvasSource(canvas, {
      codec: "avc",
      bitrate: QUALITY_HIGH,
    });

    output.addVideoTrack(videoSource, { frameRate: fps });

    // 5. Start Output
    await output.start();

    // 6. Process Audio Data
    if (audioSource && videoItems.length > 0) {
      let currentAudioTime = 0;

      for (const item of videoItems) {
        if (currentAudioTime >= totalDuration) break;

        const input = new Input({
          source: new UrlSource(item.src),
          formats: ALL_FORMATS,
        });

        try {
          const audioTrack = await input.getPrimaryAudioTrack();
          if (audioTrack) {
            const decodable = await audioTrack.canDecode();
            if (decodable) {
              const sink = new AudioBufferSink(audioTrack);
              const remainingDuration = totalDuration - currentAudioTime;
              const durationToExtract = Math.min(
                item.duration,
                remainingDuration
              );

              for await (const { buffer } of sink.buffers(
                0,
                durationToExtract
              )) {
                await audioSource.add(buffer);
              }
              currentAudioTime += durationToExtract;
            }
          }
        } catch (e) {
          console.warn(`Failed to extract audio from ${item.src}`, e);
        } finally {
          input.dispose();
        }
      }
      audioSource.close();
    }

    // 7. Process Video Data
    const dt = 1 / fps;
    const frameCount = Math.ceil(totalDuration * fps);
    const videoElements = editor.getVideoElements();

    // Stop the shared ticker
    app.ticker.stop();

    try {
      for (let i = 0; i < frameCount; i++) {
        const currentTime = i * dt;
        if (onProgress) onProgress(i / frameCount);

        // Update editor state
        editor.update(currentTime, false, true, true);

        // Wait for active video to seek if necessary
        const activeItem = timeline.items.find(
          (item) =>
            item.type === "video" &&
            currentTime >= item.startTime &&
            currentTime < item.startTime + item.duration
        ) as TimelineItemVideo | undefined;

        if (activeItem) {
          const videoElData = videoElements.get(activeItem.src);
          if (videoElData) {
            const video = videoElData.video;

            // Wait for seeking to complete
            if (video.seeking) {
              await new Promise<void>((resolve) => {
                const handler = () => {
                  video.removeEventListener("seeked", handler);
                  resolve();
                };
                video.addEventListener("seeked", handler, { once: true });
              });
            }

            // Wait for data availability
            if (video.readyState < 2) {
              await new Promise<void>((resolve) => {
                const handler = () => {
                  if (video.readyState >= 2) {
                    video.removeEventListener("canplay", handler);
                    resolve();
                  }
                };
                video.addEventListener("canplay", handler);
                if (video.readyState >= 2) {
                  video.removeEventListener("canplay", handler);
                  resolve();
                }
              });
            }
          }
        }

        // Force render
        app.render();

        // Add frame
        await videoSource.add(currentTime, dt);
      }
    } finally {
      // Restart the ticker
      app.ticker.start();
    }

    videoSource.close();
    await output.finalize();

    if (!output.target.buffer) {
      throw new Error("Output buffer is null");
    }

    return new Uint8Array(output.target.buffer as ArrayBuffer);
  }
}
