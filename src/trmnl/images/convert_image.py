import os
from PIL import Image
from pathlib import Path

MAX_BYTES = 90000
BARB_IMAGE = Path(__file__).parent / "barb.png"


def image_to_bmp(input_path: str | Path, output_filename: str = "current.bmp"):
    input_path = str(input_path)
    # 1. Load source image (any format Pillow supports)
    image = Image.open(input_path)

    # 2. Ensure 800x480 sizing for TRMNL
    # If you want strict stretch, use resize.
    # If you want to preserve aspect ratio, we can change this later.
    image = image.resize((800, 480))

    # 3. Convert to 1-bit with Floyd–Steinberg dithering (same as html_to_bmp)
    final_bmp = image.convert("1")

    # 5. Save as BMP
    final_bmp.save(output_filename)

    # 6. Enforce TRMNL’s 90 KB limit (defensive)
    size = os.path.getsize(output_filename)
    if size > MAX_BYTES:
        raise RuntimeError(
            f"{output_filename} is {size} bytes, exceeds {MAX_BYTES} byte limit"
        )

    print(f"Generated {output_filename} ({size} bytes)")


if __name__ == "__main__":
    image_to_bmp(BARB_IMAGE, "barb_converted.bmp")
