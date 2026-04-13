# tests/test_router.py
from __future__ import annotations
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from trmnl.engines.router import EngineRouter, MixEngine


@pytest.mark.asyncio
async def test_mix_engine_round_robin():
    mock_a = MagicMock()
    mock_a.next = AsyncMock(return_value=Path("/a.bmp"))
    mock_b = MagicMock()
    mock_b.next = AsyncMock(return_value=Path("/b.bmp"))

    engine = MixEngine([mock_a, mock_b])
    assert await engine.next() == Path("/a.bmp")
    assert await engine.next() == Path("/b.bmp")
    assert await engine.next() == Path("/a.bmp")  # wraps around


@pytest.mark.asyncio
async def test_mix_engine_single():
    mock = MagicMock()
    mock.next = AsyncMock(return_value=Path("/only.bmp"))
    engine = MixEngine([mock])
    assert await engine.next() == Path("/only.bmp")
    assert await engine.next() == Path("/only.bmp")


def test_mix_engine_empty_raises():
    with pytest.raises(ValueError, match="at least one engine"):
        MixEngine([])


@pytest.mark.asyncio
async def test_engine_router_tracks_last_served():
    mock_engine = MagicMock()
    mock_engine.next = AsyncMock(side_effect=[Path("/first.bmp"), Path("/second.bmp")])

    router = EngineRouter(mock_engine, "poem", [])
    assert router.last_served is None

    path = await router.next()
    assert path == Path("/first.bmp")
    assert router.last_served == Path("/first.bmp")

    path2 = await router.next()
    assert path2 == Path("/second.bmp")
    assert router.last_served == Path("/second.bmp")


def test_engine_router_set_engine_updates_state():
    mock_a = MagicMock()
    mock_b = MagicMock()

    router = EngineRouter(mock_a, "poem", [])
    assert router.active_name == "poem"
    assert router.active_sequence == []

    router.set_engine(mock_b, "mix", ["poem", "fantasy"])
    assert router.active_engine is mock_b
    assert router.active_name == "mix"
    assert router.active_sequence == ["poem", "fantasy"]
