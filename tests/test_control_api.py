# tests/test_control_api.py
from __future__ import annotations
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from trmnl.engines.router import EngineRouter


@pytest.fixture
def client():
    from trmnl.app import app
    from trmnl.engines.router import EngineRouter

    mock_engine = MagicMock()
    mock_engine.next = AsyncMock(return_value=Path("/tmp/test.bmp"))
    router = EngineRouter(mock_engine, "fantasy", [])
    router.last_served = Path("/tmp/fantasy_dragon_hoard.bmp")

    mock_image = MagicMock()
    mock_image.filename = "abc123"
    mock_image.path = Path("/tmp/abc123.bmp")
    mock_carousel = MagicMock()
    mock_carousel.next = AsyncMock(return_value=mock_image)
    mock_carousel.current = AsyncMock(return_value=mock_image)

    with patch("trmnl.app.build_engine_from_config", return_value=(mock_engine, "fantasy", [])):
        with patch("trmnl.app.Carousel", return_value=mock_carousel):
            with patch("trmnl.app.EngineRouter", return_value=router):
                with patch("trmnl.control._write_config"):
                    with TestClient(app, raise_server_exceptions=True) as tc:
                        yield tc


def test_status_returns_engine_info(client):
    resp = client.get("/api/control/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["engine"] == "fantasy"
    assert "last_served" in data


def test_engines_list(client):
    resp = client.get("/api/control/engines")
    assert resp.status_code == 200
    engines = resp.json()["engines"]
    assert "poem" in engines
    assert "fantasy" in engines


def test_set_engine_unknown_returns_400(client):
    resp = client.post("/api/control/engine", json={"engine": "bogus"})
    assert resp.status_code == 400
    assert "bogus" in resp.json()["detail"]


def test_set_engine_valid(client):
    resp = client.post("/api/control/engine", json={"engine": "fantasy"})
    assert resp.status_code == 200
    assert resp.json()["engine"] == "fantasy"


def test_control_next(client):
    resp = client.post("/api/control/next", json={})
    assert resp.status_code == 200
    assert "image" in resp.json()


def test_ping(client):
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
