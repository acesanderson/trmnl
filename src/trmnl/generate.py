from playwright.async_api import async_playwright
from PIL import Image
import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def generate_bmp_from_html(
    html_content: str, output_filename: str | Path
) -> Path:
    logger.info(f"Generating {output_filename} from HTML content.")

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body, html {{ margin: 0; padding: 0; width: 800px; height: 480px; overflow: hidden; }}
            body {{ font-family: sans-serif; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 800, "height": 480})

        await page.set_content(full_html)

        png_data: bytes = await page.screenshot()
        await browser.close()

    image = Image.open(io.BytesIO(png_data))
    final_bmp = image.convert("1")
    final_bmp.save(output_filename)

    return Path(output_filename)
