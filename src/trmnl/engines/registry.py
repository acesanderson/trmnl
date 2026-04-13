# src/trmnl/engines/registry.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trmnl.carousel import ImageEngine


def get_engine_registry() -> dict[str, type[ImageEngine]]:
    """
    Lazy-loaded to avoid circular imports.
    Maps engine name slugs to their classes.
    Add new engines here.
    """
    from trmnl.engines.poems.engine import PoemEngine
    from trmnl.engines.fantasy.engine import FantasyEngine
    from trmnl.engines.illustration.engine import IllustrationEngine

    return {
        "poem": PoemEngine,
        "fantasy": FantasyEngine,
        "illustration": IllustrationEngine,
    }
