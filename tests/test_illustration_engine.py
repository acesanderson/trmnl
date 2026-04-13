# tests/test_illustration_engine.py
from __future__ import annotations
import pytest
from pathlib import Path
import trmnl.engines.illustration.engine as illustration_mod


@pytest.mark.asyncio
async def test_illustration_engine_empty_cache_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(illustration_mod, "ILLUSTRATION_DIR", tmp_path)

    engine = illustration_mod.IllustrationEngine()
    with pytest.raises(RuntimeError, match="curate_illustrations"):
        await engine.next()


@pytest.mark.asyncio
async def test_illustration_engine_returns_bmp_path(tmp_path, monkeypatch):
    (tmp_path / "beardsley_salome.bmp").write_bytes(b"BM fake bmp content")
    monkeypatch.setattr(illustration_mod, "ILLUSTRATION_DIR", tmp_path)

    engine = illustration_mod.IllustrationEngine()
    path = await engine.next()

    assert path.suffix == ".bmp"
    assert path.parent == tmp_path


@pytest.mark.asyncio
async def test_illustration_engine_only_returns_bmps(tmp_path, monkeypatch):
    (tmp_path / "escher_relativity.bmp").write_bytes(b"BM")
    (tmp_path / "stray.png").write_bytes(b"PNG")
    monkeypatch.setattr(illustration_mod, "ILLUSTRATION_DIR", tmp_path)

    engine = illustration_mod.IllustrationEngine()
    for _ in range(10):
        path = await engine.next()
        assert path.suffix == ".bmp"
