# src/trmnl/config.py
from __future__ import annotations
from dataclasses import dataclass
from xdg_base_dirs import xdg_cache_home
from pathlib import Path
from typing import TYPE_CHECKING
import logging
import yaml

from trmnl.engines.registry import get_engine_registry

if TYPE_CHECKING:
    from trmnl.carousel import ImageEngine

logger = logging.getLogger(__name__)

CACHE_DIR = xdg_cache_home() / "trmnl"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CURRENT_IMAGE_DIR = CACHE_DIR / "working"
CURRENT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = Path.home() / ".config" / "trmnl" / "config.yaml"
_DEFAULT_ENGINE = "mix"
_DEFAULT_SEQUENCE = ["poem", "fantasy"]


@dataclass
class Settings:
    paths: dict[str, Path]
    refresh_interval: int
    server_ip: str
    port: int

    @property
    def server_url(self) -> str:
        return f"http://{self.server_ip}:{self.port}"


def build_engine_from_config() -> tuple[ImageEngine, str, list[str]]:
    """
    Reads ~/.config/trmnl/config.yaml and returns (engine, name, sequence).
    Falls back to default mix on any error — never raises.
    """
    registry = get_engine_registry()

    name = _DEFAULT_ENGINE
    sequence = list(_DEFAULT_SEQUENCE)

    extra: dict = {}
    try:
        if CONFIG_FILE.exists():
            with CONFIG_FILE.open() as f:
                data = yaml.safe_load(f) or {}
            name = data.get("engine", _DEFAULT_ENGINE)
            sequence = data.get("sequence", list(_DEFAULT_SEQUENCE))
            if data.get("artist"):
                extra["artist"] = data["artist"]
            if data.get("artists"):
                extra["artists"] = data["artists"]
    except Exception as e:
        logger.warning(f"config.yaml missing/unparseable ({e}), defaulting to mix")
        name = _DEFAULT_ENGINE
        sequence = list(_DEFAULT_SEQUENCE)

    if name != "mix" and name not in registry:
        logger.warning(f"Unknown engine '{name}' in config, defaulting to mix")
        name = _DEFAULT_ENGINE
        sequence = list(_DEFAULT_SEQUENCE)

    return _instantiate_engine(name, sequence, registry, extra=extra)


def _instantiate_engine(
    name: str, sequence: list[str], registry: dict[str, type], extra: dict | None = None
) -> tuple[ImageEngine, str, list[str]]:
    extra = extra or {}
    if name == "mix":
        from trmnl.engines.router import MixEngine
        valid = [s for s in sequence if s in registry]
        if not valid:
            valid = list(registry.keys())
        engines = [registry[s]() for s in valid]
        return MixEngine(engines), "mix", valid
    else:
        return registry[name](**extra), name, []


def load_settings() -> Settings:
    return Settings(
        paths={
            "CACHE_DIR": CACHE_DIR,
            "CURRENT_IMAGE_DIR": CURRENT_IMAGE_DIR,
        },
        refresh_interval=60,
        server_ip="10.0.0.82",
        port=8070,
    )


settings = load_settings()
