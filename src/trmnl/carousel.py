from trmnl.config import settings
from typing import Protocol
from pathlib import Path
import uuid


class ImageEngine(Protocol):
    """
    Generator-esque interface for providing image paths.
    An ImageEngine must implement a next() method that returns the Path to the next image,
    and expose the path to its image directory via the image_dir property, for dynamically
    constructing image paths.
    """

    async def next(self) -> Path: ...


class TRMNLImage:
    """
    Represents an image for TRMNL with its URL and filename.
    """

    def __init__(self, path: Path):
        self.path = path
        self.filename = path.stem
        self.image_url = f"{settings.server_url}/api/image/{self.path.name}"


class Carousel:
    """
    Manages the TRMNL working directory:

    - ensures only one BMP in working_dir
    - copies the next source image into working_dir
    - uses a unique filename each time
    """

    def __init__(
        self,
        engine: ImageEngine,
        working_dir: Path = settings.paths["CURRENT_IMAGE_DIR"],
    ):
        self.engine: ImageEngine = engine
        self.working_dir: Path = working_dir

    async def current(self) -> TRMNLImage:
        """Get the current available image to be displayed."""
        await self._ensure_single_image()
        bmp_files = list(self.working_dir.glob("*.bmp"))
        if not bmp_files:
            raise FileNotFoundError("No BMP file found in directory.")
        return TRMNLImage(bmp_files[0])

    async def next(self) -> TRMNLImage:
        """
        Advance to the next image to be displayed and return the Path to the app.
        """
        await self._ensure_single_image()  # clean up any old images

        # ask the injected generator for the next source image
        src = await self.engine.next()
        self._validate_image_path(src)

        # Create unique filename in working_dir
        unique_filename = f"{uuid.uuid4()}.bmp"
        dest = settings.paths["CURRENT_IMAGE_DIR"] / unique_filename

        with src.open("rb") as f_in, dest.open("wb") as f_out:
            _ = f_out.write(f_in.read())

        await self._ensure_single_image()  # clean up any old images

        assert dest.exists(), "Failed to copy image to working directory."
        return TRMNLImage(dest)

    async def _ensure_single_image(self) -> None:
        bmp_files = list(self.working_dir.glob("*.bmp"))
        if len(bmp_files) > 1:
            bmp_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for file in bmp_files[1:]:
                file.unlink()

    def _validate_image_path(self, path: Path) -> None:
        """
        Validate that the provided path is a BMP file and not in the working directory.
        """
        if path.suffix.lower() != ".bmp":
            raise ValueError("Image must be a BMP file.")
        if path.parent == settings.paths["CURRENT_IMAGE_DIR"]:
            raise ValueError("Source image cannot be in the working directory.")


if __name__ == "__main__":
    # test TRMNLImage; create mock TRMNLImage object
    test_path = Path("/path/to/image.bmp")
    trmnl_image = TRMNLImage(test_path)
