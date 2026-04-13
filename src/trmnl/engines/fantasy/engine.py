# src/trmnl/engines/fantasy/engine.py
from __future__ import annotations
from trmnl.config import settings
from pathlib import Path
import random
import logging

logger = logging.getLogger(__name__)

FANTASY_DIR = settings.paths["CACHE_DIR"] / "fantasy"
FANTASY_DIR.mkdir(parents=True, exist_ok=True)


class FantasyEngine:
    def __init__(self) -> None:
        count = len(list(FANTASY_DIR.glob("*.bmp")))
        logger.info(f"FantasyEngine initialized with {count} cached images")

    async def next(self) -> Path:
        bmp_files = list(FANTASY_DIR.glob("*.bmp"))
        if not bmp_files:
            logger.error("FantasyEngine: no images in cache")
            raise RuntimeError(
                "No fantasy images cached. Run background_process.py first."
            )
        chosen = random.choice(bmp_files)
        logger.info(f"FantasyEngine serving: {chosen.name}")
        return chosen
