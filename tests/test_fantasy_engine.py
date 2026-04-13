# tests/test_fantasy_engine.py
from __future__ import annotations
import pytest
from pathlib import Path


@pytest.mark.asyncio
async def test_fantasy_engine_empty_cache_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("trmnl.engines.fantasy.engine.FANTASY_DIR", tmp_path)
    import importlib
    import trmnl.engines.fantasy.engine as mod
    importlib.reload(mod)

    engine = mod.FantasyEngine()
    with pytest.raises(RuntimeError, match="background_process"):
        await engine.next()


@pytest.mark.asyncio
async def test_fantasy_engine_returns_bmp_path(tmp_path, monkeypatch):
    (tmp_path / "fantasy_dragon_hoard.bmp").write_bytes(b"BM fake bmp content")
    monkeypatch.setattr("trmnl.engines.fantasy.engine.FANTASY_DIR", tmp_path)

    import importlib
    import trmnl.engines.fantasy.engine as mod
    importlib.reload(mod)

    engine = mod.FantasyEngine()
    path = await engine.next()

    assert path.suffix == ".bmp"
    assert path.parent == tmp_path


@pytest.mark.asyncio
async def test_fantasy_engine_only_returns_bmps(tmp_path, monkeypatch):
    (tmp_path / "fantasy_test.bmp").write_bytes(b"BM")
    (tmp_path / "stray.png").write_bytes(b"PNG")
    monkeypatch.setattr("trmnl.engines.fantasy.engine.FANTASY_DIR", tmp_path)

    import importlib
    import trmnl.engines.fantasy.engine as mod
    importlib.reload(mod)

    engine = mod.FantasyEngine()
    for _ in range(10):
        path = await engine.next()
        assert path.suffix == ".bmp"
