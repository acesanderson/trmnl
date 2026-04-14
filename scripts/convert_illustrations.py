# scripts/convert_illustrations.py
# Convert source images to 800x480 1-bit BMP for the IllustrationEngine.
# Usage: uv run --with pillow python scripts/convert_illustrations.py <source_dir> [--artist <name>]
#
# Without --artist: outputs to ~/.cache/trmnl/illustration/ (flat, backward compat)
# With --artist:    outputs to ~/.cache/trmnl/illustration/<artist>/
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from PIL import Image, ImageOps

TARGET = (800, 480)
EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".gif"}
BASE_DIR = Path.home() / ".cache" / "trmnl" / "illustration"


def slugify(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")[:80]


def convert(src: Path, out_dir: Path) -> None:
    slug = slugify(src.stem)
    dest = out_dir / f"{slug}.bmp"
    n = 1
    while dest.exists():
        dest = out_dir / f"{slug}_{n}.bmp"
        n += 1
    with Image.open(src) as img:
        img = img.convert("RGB")
        padded = ImageOps.pad(img, TARGET, color=0, method=Image.LANCZOS)
        bmp = padded.convert("1")
        bmp.save(dest, format="BMP")
    print(f"  {src.name} -> {dest.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert images to 800x480 1-bit BMP for IllustrationEngine"
    )
    parser.add_argument("source_dir", help="Directory of source images")
    parser.add_argument("--artist", help="Artist name — images go in illustration/<artist>/")
    args = parser.parse_args()

    src_dir = Path(args.source_dir).expanduser()
    if not src_dir.is_dir():
        print(f"Not a directory: {src_dir}")
        sys.exit(1)

    out_dir = BASE_DIR / args.artist if args.artist else BASE_DIR

    sources = [p for p in src_dir.iterdir() if p.suffix.lower() in EXTS]
    if not sources:
        print(f"No image files found in {src_dir}")
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Converting {len(sources)} images -> {out_dir}")

    errors = []
    for src in sorted(sources):
        try:
            convert(src, out_dir)
        except Exception as e:
            errors.append((src.name, e))
            print(f"  SKIP {src.name}: {e}")

    print(f"\nDone: {len(sources) - len(errors)} converted, {len(errors)} skipped.")


if __name__ == "__main__":
    main()
