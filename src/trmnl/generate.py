from playwright.sync_api import sync_playwright
from trmnl.poems.poem import random_poem
from PIL import Image
import io
import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

DIR_PATH = Path(__file__).parent.resolve()


def delete_all_bmp():
    bmp_files = DIR_PATH.glob("*.bmp")
    for bmp_file in bmp_files:
        bmp_file.unlink()
    logger.info("Deleted all existing BMP files.")


def html_to_bmp(html_content: str, output_filename: str = "current.bmp"):
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
    print(f"Generated {output_filename}")


def render_poem(title: str, poem: str, poet: str):
    # Simple HTML template for poem rendering
    # Replace newlines with <br> for HTML formatting
    poem_text = poem.replace("\n", "<br>")
    poem_html = f"""
    <div style="display: flex; justify-content: center; align-items: center; height: 80%; flex-direction: column;">
        <h1 style="font-size: 80; margin: 0;">{title.upper()}</h1>
        <h2 style="font-size: 60; margin: 0;">by {poet}</h2>
        <p>{poem_text}</p>
    </div>
    """
    delete_all_bmp()
    output_filename = f"poem_{uuid.uuid4().hex}.bmp"
    html_to_bmp(poem_html, output_filename)


def generate():
    logger.info("Generating new poem image...")
    poem_object = random_poem()
    title = poem_object["title"]
    poem = poem_object["poem"]
    poet = poem_object["poet"]
    render_poem(title, poem, poet)


if __name__ == "__main__":
    generate()
