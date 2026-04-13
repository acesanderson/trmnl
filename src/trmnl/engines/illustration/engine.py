# src/trmnl/engines/illustration/engine.py
from __future__ import annotations
from trmnl.config import settings
from pathlib import Path
import random
import logging

logger = logging.getLogger(__name__)

ILLUSTRATION_DIR = settings.paths["CACHE_DIR"] / "illustration"
ILLUSTRATION_DIR.mkdir(parents=True, exist_ok=True)


class IllustrationEngine:
    def __init__(self) -> None:
        count = len(list(ILLUSTRATION_DIR.glob("*.bmp")))
        logger.info(f"IllustrationEngine initialized with {count} cached images")

    async def next(self) -> Path:
        bmp_files = list(ILLUSTRATION_DIR.glob("*.bmp"))
        if not bmp_files:
            logger.error("IllustrationEngine: no images in cache")
            raise RuntimeError(
                "No illustration images cached. Run scripts/curate_illustrations.py first."
            )
        chosen = random.choice(bmp_files)
        logger.info(f"IllustrationEngine serving: {chosen.name}")
        return chosen
