# src/trmnl/engines/illustration/engine.py
from __future__ import annotations
from pathlib import Path
import random
import logging

from trmnl.config import settings

logger = logging.getLogger(__name__)

ILLUSTRATION_DIR = settings.paths["CACHE_DIR"] / "illustration"
ILLUSTRATION_DIR.mkdir(parents=True, exist_ok=True)


class IllustrationEngine:
    def __init__(
        self,
        artist: str | None = None,
        artists: list[str] | None = None,
    ) -> None:
        if artist and artists:
            raise ValueError("Specify artist or artists, not both")

        if artist:
            self._dirs = [ILLUSTRATION_DIR / artist]
        elif artists:
            self._dirs = [ILLUSTRATION_DIR / a for a in artists]
        else:
            # flat dir fallback — backward compat
            self._dirs = [ILLUSTRATION_DIR]

        self._index = 0

        total = sum(len(list(d.glob("*.bmp"))) for d in self._dirs if d.exists())
        artists_desc = artist or (", ".join(artists) if artists else "all")
        logger.info(f"IllustrationEngine initialized: {total} images [{artists_desc}]")

    async def next(self) -> Path:
        if len(self._dirs) == 1:
            bmp_files = list(self._dirs[0].glob("*.bmp"))
        else:
            d = self._dirs[self._index]
            self._index = (self._index + 1) % len(self._dirs)
            bmp_files = list(d.glob("*.bmp"))

        if not bmp_files:
            raise RuntimeError(
                "No illustration images cached. "
                "Run scripts/convert_illustrations.py --artist <name> first."
            )
        chosen = random.choice(bmp_files)
        logger.info(f"IllustrationEngine serving: {chosen.name}")
        return chosen
