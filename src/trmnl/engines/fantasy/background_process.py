# src/trmnl/engines/fantasy/background_process.py
"""
Idempotent image generator for the FantasyEngine cache.
Run locally (not on caruana) -- requires OPENAI_API_KEY in environment.

Usage:
    uv run python src/trmnl/engines/fantasy/background_process.py

Costs ~$0.08 per image (DALL-E 3 hd quality). Skips already-cached slugs.
Add new entries to PROMPTS and re-run to extend the cache.
"""
from __future__ import annotations
import asyncio
import base64
import io
import logging
from pathlib import Path

from PIL import Image, ImageOps
from rich.console import Console

from trmnl.config import settings
from trmnl.engines.fantasy.prompts import STYLE_PREAMBLE, PROMPTS

console = Console()
logger = logging.getLogger(__name__)

FANTASY_DIR = settings.paths["CACHE_DIR"] / "fantasy"
FANTASY_DIR.mkdir(parents=True, exist_ok=True)


async def _generate_one(slug: str, prompt: str) -> bool:
    """Generate and save one BMP. Returns True on success."""
    from conduit.core.model.model_async import ModelAsync

    output_path = FANTASY_DIR / f"fantasy_{slug}.bmp"
    tmp_path = FANTASY_DIR / f"fantasy_{slug}.bmp.tmp"
    full_prompt = f"{STYLE_PREAMBLE} {prompt}"

    try:
        model = ModelAsync("dall-e-3")
        response = await model.image.generate(
            prompt_str=full_prompt,
            size="1792x1024",
            quality="hd",
            style="natural",
            response_format="b64_json",
        )
    except Exception as e:
        console.print(f"[red]Failed {slug}[/red]: {e}")
        return False

    images = response.message.images
    if not images:
        console.print(f"[red]Failed {slug}[/red]: empty response from API")
        return False

    image_data = base64.b64decode(images[0].b64_json)
    image = Image.open(io.BytesIO(image_data))
    image = ImageOps.pad(image, (800, 480), color=(0, 0, 0))
    bmp = image.convert("1")
    bmp.save(tmp_path, format="BMP")
    tmp_path.rename(output_path)

    size = output_path.stat().st_size
    console.print(f"[green]Generated {slug}[/green] -> {output_path.name} ({size} bytes)")
    return True


async def run() -> None:
    n_generated = n_skipped = n_failed = 0

    for entry in PROMPTS:
        slug = entry["slug"]
        output_path = FANTASY_DIR / f"fantasy_{slug}.bmp"

        if output_path.exists():
            console.print(f"[blue]Skipping {slug} (already cached)[/blue]")
            n_skipped += 1
            continue

        success = await _generate_one(slug, entry["prompt"])
        if success:
            n_generated += 1
        else:
            n_failed += 1

    console.print(
        f"\nDone: [green]{n_generated} generated[/green], "
        f"[blue]{n_skipped} skipped[/blue], "
        f"[red]{n_failed} failed[/red]"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(run())
