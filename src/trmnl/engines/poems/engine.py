from trmnl.config import settings
from trmnl.carousel import ImageEngine
from trmnl.generate import generate_bmp_from_html
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

CACHE_DIR = settings.paths["CACHE_DIR"]
POEMS_DIR = CACHE_DIR / "poems"
POEMS_DIR.mkdir(parents=True, exist_ok=True)


class PoemEngine(ImageEngine):
    async def next(self) -> Path:
        poem_object = await self._retrieve_poem()
        title = poem_object["title"]
        poem = poem_object["poem"]
        poet = poem_object["poet"]
        poem_image_path = await self._generate_poem_image(title, poem, poet)
        return poem_image_path

    @property
    def image_dir(self) -> Path:
        return POEMS_DIR

    async def _retrieve_poem(self) -> dict[str, str]:
        from trmnl.engines.poems.poem import random_poem

        poem_object: dict[str, str] = await random_poem()
        return poem_object

    async def _generate_poem_image(self, title: str, poem: str, poet: str) -> Path:
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
            <b><p>{title.upper()} by {poet}</p></b>
            <p>{poem_text}</p>
        </div>
        """
        new_path = await generate_bmp_from_html(poem_html, output_filename)
        return new_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = PoemEngine()
    poem_image = engine.next()
    logger.info(f"Generated poem image at: {poem_image}")
