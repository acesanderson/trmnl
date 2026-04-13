# src/trmnl/engines/router.py
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from trmnl.carousel import ImageEngine

logger = logging.getLogger(__name__)


class MixEngine:
    def __init__(self, engines: list[ImageEngine]):
        if not engines:
            raise ValueError("MixEngine requires at least one engine")
        self.engines = engines
        self._index = 0

    async def next(self) -> Path:
        engine = self.engines[self._index]
        current = self._index
        self._index = (self._index + 1) % len(self.engines)
        # Note: _index is not concurrency-safe in a concurrent async context.
        # Two concurrent callers could read the same index before either increments it.
        # This is fine for the single-consumer use case here.
        logger.debug(f"MixEngine: index {current} -> {self._index}")
        return await engine.next()


class EngineRouter:
    def __init__(self, engine: ImageEngine, name: str, sequence: list[str]):
        self.active_engine: ImageEngine = engine
        self.active_name: str = name
        self.active_sequence: list[str] = sequence
        self.last_served: Path | None = None

    async def next(self) -> Path:
        path = await self.active_engine.next()
        self.last_served = path
        return path

    def set_engine(self, engine: ImageEngine, name: str, sequence: list[str]) -> None:
        self.active_engine = engine
        self.active_name = name
        self.active_sequence = sequence
        logger.info(f"Engine switched to {name} (sequence: {sequence})")
