from playwright.sync_api import sync_playwright
from PIL import Image
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_bmp_from_html(html_content: str, output_filename: str | Path) -> Path:
    logger.info(f"Generating {output_filename} from HTML content.")
    # 1. Inject TRMNL-specific CSS reset to ensure exact 800x480 sizing
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body, html {{ margin: 0; padding: 0; width: 800px; height: 480px; overflow: hidden; }}
            /* Optional: Default font for cleaner look */
            body {{ font-family: sans-serif; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    with sync_playwright() as p:
        # 2. Launch Headless Browser
        browser = p.chromium.launch()
        # Set exact viewport for TRMNL
        page = browser.new_page(viewport={"width": 800, "height": 480})
        page.set_content(full_html)

        # 3. Capture Screenshot (returned as bytes)
        png_data = page.screenshot()
        browser.close()

    # 4. Process with Pillow (Convert to 1-bit Dithered BMP)
    image = Image.open(io.BytesIO(png_data))

    # .convert("1") automatically applies Floyd-Steinberg dithering by default
    # If you wanted threshold (solid black/white), you would use .convert("1", dither=Image.NONE)
    final_bmp = image.convert("1")

    final_bmp.save(output_filename)
    return Path(output_filename)
