# tests/test_config.py
from __future__ import annotations
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from trmnl.engines.router import MixEngine


def _mock_registry():
    """Returns a minimal fake registry with poem and fantasy stubs."""
    mock_poem = MagicMock()
    mock_poem.return_value = MagicMock()  # PoemEngine instance
    mock_fantasy = MagicMock()
    mock_fantasy.return_value = MagicMock()  # FantasyEngine instance
    return {"poem": mock_poem, "fantasy": mock_fantasy}


def test_build_engine_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("trmnl.config.CONFIG_FILE", tmp_path / "nonexistent.yaml")
    with patch("trmnl.config.get_engine_registry", return_value=_mock_registry()):
        from trmnl.config import build_engine_from_config
        engine, name, sequence = build_engine_from_config()
    assert name == "mix"
    assert isinstance(engine, MixEngine)


def test_build_engine_reads_single(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("engine: fantasy\n")
    monkeypatch.setattr("trmnl.config.CONFIG_FILE", cfg)
    with patch("trmnl.config.get_engine_registry", return_value=_mock_registry()):
        from trmnl.config import build_engine_from_config
        engine, name, sequence = build_engine_from_config()
    assert name == "fantasy"
    assert sequence == []


def test_build_engine_reads_mix(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("engine: mix\nsequence:\n  - poem\n  - fantasy\n")
    monkeypatch.setattr("trmnl.config.CONFIG_FILE", cfg)
    with patch("trmnl.config.get_engine_registry", return_value=_mock_registry()):
        from trmnl.config import build_engine_from_config
        engine, name, sequence = build_engine_from_config()
    assert name == "mix"
    assert sequence == ["poem", "fantasy"]
    assert isinstance(engine, MixEngine)


def test_build_engine_malformed_file(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(": : invalid yaml : :")
    monkeypatch.setattr("trmnl.config.CONFIG_FILE", cfg)
    with patch("trmnl.config.get_engine_registry", return_value=_mock_registry()):
        from trmnl.config import build_engine_from_config
        engine, name, sequence = build_engine_from_config()
    assert name == "mix"


def test_build_engine_unknown_engine_name(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("engine: nonexistent\n")
    monkeypatch.setattr("trmnl.config.CONFIG_FILE", cfg)
    with patch("trmnl.config.get_engine_registry", return_value=_mock_registry()):
        from trmnl.config import build_engine_from_config
        engine, name, sequence = build_engine_from_config()
    assert name == "mix"
