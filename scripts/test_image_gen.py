#!/usr/bin/env python3
"""
Generate BMP variants of one scene with different style prompts.
Run: uv run python scripts/test_image_gen.py
Output: <project_root>/test_output/test_0.bmp ... test_5.bmp
"""
from __future__ import annotations
import asyncio
import base64
import io
from pathlib import Path

from PIL import Image, ImageOps

OUTPUT_DIR = Path(__file__).parent.parent / "test_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCENE = "a dragon sleeping on its hoard of gold coins and jewels, curled up like a contented dog"

STYLE_VARIANTS = [
    (
        "durer",
        "Albrecht Dürer woodcut engraving style, black and white only, fine crosshatching, "
        "stark contrast, dramatic chiaroscuro, no color, no gradients, "
        "16th century German Renaissance printmaking aesthetic --",
    ),
    (
        "dore",
        "Gustave Doré engraving style, black and white only, fine crosshatching, "
        "high drama, detailed linework, no color, no gradients --",
    ),
    (
        "linocut",
        "linocut print, bold black and white, high contrast, simplified shapes, "
        "minimal detail, stark shadows --",
    ),
    (
        "medieval_manuscript",
        "medieval manuscript ink illustration, black ink on parchment, "
        "detailed pen linework, no color, flat areas --",
    ),
    (
        "pen_ink",
        "pen and ink illustration, black and white, architectural fine hatching lines, "
        "no color, no gradients --",
    ),
    (
        "woodblock",
        "Japanese woodblock print aesthetic, black and white only, bold outlines, "
        "flat areas, no gradients, stark --",
    ),
]


async def generate_variant(index: int, label: str, preamble: str) -> Path:
    from conduit.core.model.model_async import ModelAsync

    model = ModelAsync("dall-e-3")
    prompt = f"{preamble} {SCENE}"
    response = await model.image.generate(
        prompt_str=prompt,
        size="1792x1024",
        quality="hd",
        style="natural",
        response_format="b64_json",
    )
    images = response.message.images
    if not images:
        raise RuntimeError(f"Variant {index} ({label}): empty response from API")

    image_data = base64.b64decode(images[0].b64_json)
    image = Image.open(io.BytesIO(image_data))
    image = ImageOps.pad(image, (800, 480), color=(0, 0, 0))
    bmp = image.convert("1")
    output_path = OUTPUT_DIR / f"test_{index}_{label}.bmp"
    bmp.save(output_path)
    return output_path


async def main() -> None:
    print(f"Generating {len(STYLE_VARIANTS)} variants concurrently...")
    tasks = [
        generate_variant(i, label, preamble)
        for i, (label, preamble) in enumerate(STYLE_VARIANTS)
    ]
    paths = await asyncio.gather(*tasks)
    print("\nOutput files:")
    for path in paths:
        print(f"  {path}")
    print(f"\nOpen all: open {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
