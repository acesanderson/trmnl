from __future__ import annotations
from dataclasses import dataclass
from xdg_base_dirs import xdg_cache_home
from pathlib import Path
from typing import TYPE_CHECKING
from collections.abc import Callable

if TYPE_CHECKING:
    from trmnl.engine import ImageEngine

CACHE_DIR = xdg_cache_home() / "trmnl"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_IMAGE_DIR = CACHE_DIR / "working"
CURRENT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Settings:
    paths: dict[str, Path]
    default_engine: Callable[[], ImageEngine]


def default_engine() -> ImageEngine:
    """
    Lazy loader for the default image engine.
    """
    from trmnl.engines.poems.engine import PoemEngine

    return PoemEngine()


def load_settings() -> Settings:
    return Settings(
        paths={
            "CACHE_DIR": CACHE_DIR,
            "CURRENT_IMAGE_DIR": CURRENT_IMAGE_DIR,
        },
        default_engine=default_engine,
    )


settings = load_settings()
