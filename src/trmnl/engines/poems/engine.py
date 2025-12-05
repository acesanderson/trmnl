from trmnl.config import settings
from trmnl.engine import ImageEngine
from trmnl.generate import generate_bmp_from_html
from pathlib import Path
import logging
from typing import override

logger = logging.getLogger(__name__)

CACHE_DIR = settings.paths["CACHE_DIR"]
POEMS_DIR = CACHE_DIR / "poems"


class PoemEngine(ImageEngine):
    @override
    def __next__(self) -> Path:
        poem_object = self._retrieve_poem()
        title = poem_object["title"]
        poem = poem_object["poem"]
        poet = poem_object["poet"]
        poem_image_path = self._generate_poem_image(title, poem, poet)
        return poem_image_path

    def _retrieve_poem(self) -> dict[str, str]:
        from trmnl.engines.poems.poem import random_poem

        poem_object: dict[str, str] = random_poem()
        return poem_object

    def _generate_poem_image(self, title: str, poem: str, poet: str) -> Path:
        title_name = title.lower().replace(" ", "_")
        output_filename: Path = POEMS_DIR / f"poem_{title_name}.bmp"
        # If file already exists, skip generation
        if output_filename.exists():
            logger.info(
                f"Poem image {output_filename} already exists. Skipping generation."
            )
            return output_filename
        # Simple HTML template for poem rendering
        # Replace newlines with <br> for HTML formatting
        poem_text = poem.replace("\n", "<br>")
        poem_html = f"""
        <div style="display: flex; justify-content: center; align-items: center; height: 80%; flex-direction: column;">
            <h1 style="font-size: 60x; margin: 0;">{title.upper()}</h3>
            <h2 style="font-size: 40x; margin: 0;">by {poet}</h3>
            <p>{poem_text}</p>
        </div>
        """
        new_path = generate_bmp_from_html(poem_html, output_filename)
        return new_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = PoemEngine()
    poem_image = next(engine)
    logger.info(f"Generated poem image at: {poem_image}")
