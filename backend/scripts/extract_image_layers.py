import os
import json
import asyncio
import httpx
import base64
from pathlib import Path
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
import fal_client


def image_to_data_uri(image_path: Path) -> str:
    """Convert image file to data URI"""
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{image_data}"


async def download_image(url: str, output_path: Path) -> bool:
    """Download image from URL and save to local file"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()
            output_path.write_bytes(response.content)
            return True
    except Exception as e:
        print(f"[ERROR] Failed to download image: {e}")
        return False


def decompose_image_layers(image_path: Path, num_layers: int = 4) -> Optional[List[Dict[str, Any]]]:
    """
    Decompose an image into multiple RGBA layers using Qwen-Image-Layered via fal.ai.

    Args:
        image_path: Path to the input image
        num_layers: Number of layers to decompose into

    Returns:
        List of layer information with URLs, or None if failed
    """
    try:
        # Convert image to data URI
        image_uri = image_to_data_uri(image_path)

        # Call fal.ai Qwen Image Layered
        result = fal_client.subscribe(
            "fal-ai/qwen-image-layered",
            arguments={
                "image_url": image_uri,
                "num_layers": num_layers,
            },
            with_logs=True,
        )

        # Extract layers from result
        if result and "layers" in result:
            return [
                {"imageURL": layer.get("url"), "index": i}
                for i, layer in enumerate(result["layers"])
                if layer.get("url")
            ]
        elif result and "images" in result:
            return [
                {"imageURL": img.get("url"), "index": i}
                for i, img in enumerate(result["images"])
                if img.get("url")
            ]

        print(f"[DEBUG] Unexpected result structure: {result}")
        return None

    except Exception as e:
        print(f"[ERROR] Qwen layer decomposition failed: {e}")
        return None


async def main():
    load_dotenv()

    # Set fal.ai API key
    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        raise ValueError("FAL_KEY not found in environment variables.")
    os.environ["FAL_KEY"] = fal_key

    base_dir = Path(__file__).resolve().parent
    output_base = base_dir.parent / "output"

    # Input: Generated keyframe images from Flux
    input_dir = output_base / "keyframe_images_flux_02"

    if not input_dir.exists():
        raise FileNotFoundError(f"Keyframe images directory not found: {input_dir}")

    # Output: Extracted layers for each keyframe
    output_dir = output_base / "keyframe_layers_02"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("[INFO] Using fal.ai Qwen-Image-Layered")

    # Get all keyframe images
    image_files = sorted(input_dir.glob("*.png"))
    print(f"[INFO] Found {len(image_files)} keyframe images to process")

    # Statistics
    total_processed = 0
    total_failed = 0
    total_layers_extracted = 0

    for image_path in image_files:
        kf_id = image_path.stem  # e.g., "KF_B1_01"

        # Create output subdirectory for this keyframe's layers
        kf_output_dir = output_dir / kf_id

        # Check if already processed
        if kf_output_dir.exists() and any(kf_output_dir.glob("layer_*.png")):
            print(f"[INFO] Layers already exist for {kf_id}, skipping")
            continue

        kf_output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n[INFO] Processing {kf_id}...")
        print(f"[INFO] Input: {image_path}")

        # Decompose into layers
        layers = decompose_image_layers(
            image_path=image_path,
            num_layers=4,  # Extract 4 layers: background, mid-ground, foreground, characters
        )

        if not layers:
            print(f"[WARN] No layers returned for {kf_id}")
            total_failed += 1
            continue

        # Download and save each layer
        layers_saved = 0
        for layer_info in layers:
            layer_idx = layer_info["index"]
            layer_url = layer_info["imageURL"]
            layer_path = kf_output_dir / f"layer_{layer_idx:02d}.png"

            print(f"[INFO] Downloading layer {layer_idx} from: {layer_url[:80]}...")
            success = await download_image(layer_url, layer_path)

            if success:
                layers_saved += 1
                print(f"[INFO] Saved: {layer_path}")
            else:
                print(f"[ERROR] Failed to save layer {layer_idx}")

        if layers_saved > 0:
            total_processed += 1
            total_layers_extracted += layers_saved

            # Save layer metadata
            metadata = {
                "source_image": str(image_path),
                "kf_id": kf_id,
                "num_layers": layers_saved,
                "layers": [
                    {
                        "index": layer_info["index"],
                        "file": f"layer_{layer_info['index']:02d}.png",
                    }
                    for layer_info in layers[:layers_saved]
                ]
            }
            metadata_path = kf_output_dir / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2))
            print(f"[INFO] Saved metadata: {metadata_path}")
        else:
            total_failed += 1

    # Summary
    print("\n" + "="*60)
    print("LAYER EXTRACTION SUMMARY")
    print("="*60)
    print(f"Provider:                fal.ai")
    print(f"Model:                   qwen-image-layered")
    print(f"Images Processed:        {total_processed}")
    print(f"Images Failed:           {total_failed}")
    print(f"Total Layers Extracted:  {total_layers_extracted}")
    print(f"Output Directory:        {output_dir}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
