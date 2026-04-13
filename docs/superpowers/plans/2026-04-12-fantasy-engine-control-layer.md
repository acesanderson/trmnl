# Fantasy Engine & Control Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `FantasyEngine` (AI-generated Dürer-style BMPs via DALL-E 3) and a runtime control layer (EngineRouter, MixEngine, admin API, `trmnl-ctl` CLI) that lets any client device switch engines without restarting the server.

**Architecture:** A new `EngineRouter` wraps the active engine and is stored in `app.state`; the `Carousel` holds the router rather than an engine directly, enabling hot-swap. A `MixEngine` wraps multiple engines in a user-defined round-robin sequence. A YAML config file on caruana persists the active selection across restarts. The `FantasyEngine` is purely cache-driven at runtime — DALL-E 3 is only called by a separate background script run locally.

**Tech Stack:** FastAPI, Pydantic, httpx (CLI HTTP client), pyyaml, Pillow, conduit `ModelAsync("dall-e-3")`, pytest + pytest-asyncio, Rich (background process console output), systemd (caruana daemon)

---

## File Map

**New files:**
| File | Responsibility |
|------|---------------|
| `src/trmnl/engines/__init__.py` | Empty namespace marker |
| `src/trmnl/engines/registry.py` | `get_engine_registry()` — maps name slugs → engine classes |
| `src/trmnl/engines/router.py` | `MixEngine` + `EngineRouter` |
| `src/trmnl/engines/fantasy/__init__.py` | Empty namespace marker |
| `src/trmnl/engines/fantasy/prompts.py` | `STYLE_PREAMBLE` + `PROMPTS` list |
| `src/trmnl/engines/fantasy/engine.py` | `FantasyEngine` — random BMP from cache |
| `src/trmnl/engines/fantasy/background_process.py` | Idempotent image generator (run locally) |
| `src/trmnl/control.py` | FastAPI `APIRouter` for `/api/control/*` |
| `src/trmnl/cli.py` | `trmnl-ctl` entry point |
| `scripts/test_image_gen.py` | Concurrent style-variant generator for eyeballing |
| `scripts/deploy.sh` | push → pull caruana → uv sync → restart → poll /ping |
| `tests/test_router.py` | MixEngine + EngineRouter unit tests |
| `tests/test_fantasy_engine.py` | FantasyEngine unit tests |
| `tests/test_config.py` | `build_engine_from_config()` unit tests |
| `tests/test_control_api.py` | Admin endpoint integration tests |

**Modified files:**
| File | Change |
|------|--------|
| `pyproject.toml` | Add `httpx`, `pyyaml`; add `trmnl-ctl` entry point; add `[tool.pytest.ini_options]`; add `[project.optional-dependencies].dev` |
| `src/trmnl/config.py` | Remove `default_engine` field from `Settings`; add `CONFIG_FILE`; add `build_engine_from_config()` |
| `src/trmnl/app.py` | Update `lifespan` to use `build_engine_from_config()` + `EngineRouter`; add `GET /ping`; mount control router |

---

## Task 1: Project setup — pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add production deps, entry point, and pytest config**

Replace the full `pyproject.toml` with:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "trmnl"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "conduit",
    "fastapi>=0.123.5",
    "httpx>=0.27.0",
    "kagglehub>=0.3.13",
    "levenshtein>=0.27.3",
    "lorem>=0.1.1",
    "pandas>=2.3.3",
    "pillow>=12.0.0",
    "playwright>=1.56.0",
    "pydantic>=2.12.5",
    "python-levenshtein>=0.27.3",
    "pyyaml>=6.0.0",
    "rich>=14.2.0",
    "uvicorn>=0.38.0",
    "xdg-base-dirs>=6.0.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.hatch.build.targets.wheel]
packages = ["src/trmnl"]
sources = ["src"]

[tool.hatch.build.targets.sdist]
include = ["src/trmnl/py.typed"]

[tool.uv.sources]
conduit = { path = "../conduit-project", editable = true }

[project.scripts]
trmnl = "trmnl.main:main"
trmnl-ctl = "trmnl.cli:main"
```

- [ ] **Step 2: Sync deps**

```bash
uv sync --extra dev
```

Expected: resolves httpx, pyyaml, pytest, pytest-asyncio.

- [ ] **Step 3: Verify pytest runs**

```bash
uv run pytest tests/ -v
```

Expected: `test_sanity PASSED`, 1 passed.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add httpx, pyyaml, pytest-asyncio; add trmnl-ctl entry point"
```

---

## Task 2: Engine namespace markers

**Files:**
- Create: `src/trmnl/engines/__init__.py`
- Create: `src/trmnl/engines/fantasy/__init__.py`

- [ ] **Step 1: Create both empty `__init__.py` files**

```bash
touch src/trmnl/engines/__init__.py src/trmnl/engines/fantasy/__init__.py
```

- [ ] **Step 2: Commit**

```bash
git add src/trmnl/engines/__init__.py src/trmnl/engines/fantasy/__init__.py
git commit -m "chore: add engines namespace __init__ files"
```

---

## Task 3: Engine Registry

**Files:**
- Create: `src/trmnl/engines/registry.py`

- [ ] **Step 1: Write the file**

```python
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

    return {
        "poem": PoemEngine,
        "fantasy": FantasyEngine,
    }
```

- [ ] **Step 2: Verify importable**

```bash
uv run python -c "from trmnl.engines.registry import get_engine_registry; print(list(get_engine_registry().keys()))"
```

Expected: `['poem', 'fantasy']`

- [ ] **Step 3: Commit**

```bash
git add src/trmnl/engines/registry.py
git commit -m "feat: add engine registry"
```

---

## Task 4: MixEngine + EngineRouter

**Files:**
- Create: `src/trmnl/engines/router.py`
- Create: `tests/test_router.py`

- [ ] **Step 1: Write the failing tests**

```python
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
    mock_engine.next = AsyncMock(return_value=Path("/served.bmp"))

    router = EngineRouter(mock_engine, "poem", [])
    assert router.last_served is None

    path = await router.next()
    assert path == Path("/served.bmp")
    assert router.last_served == Path("/served.bmp")


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
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
uv run pytest tests/test_router.py -v
```

Expected: `ImportError: cannot import name 'EngineRouter'`

- [ ] **Step 3: Implement router.py**

```python
# src/trmnl/engines/router.py
from __future__ import annotations
from pathlib import Path
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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
        logger.debug(f"MixEngine: index {current} → {self._index}")
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
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
uv run pytest tests/test_router.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/trmnl/engines/router.py tests/test_router.py
git commit -m "feat: add MixEngine and EngineRouter"
```

---

## Task 5: build_engine_from_config()

**Files:**
- Modify: `src/trmnl/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config.py
from __future__ import annotations
import pytest
import yaml
from pathlib import Path
from trmnl.engines.router import MixEngine


def test_build_engine_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr("trmnl.config.CONFIG_FILE", tmp_path / "nonexistent.yaml")
    from trmnl.config import build_engine_from_config
    engine, name, sequence = build_engine_from_config()
    assert name == "mix"
    assert isinstance(engine, MixEngine)


def test_build_engine_reads_single(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("engine: fantasy\n")
    monkeypatch.setattr("trmnl.config.CONFIG_FILE", cfg)
    from trmnl.config import build_engine_from_config
    engine, name, sequence = build_engine_from_config()
    assert name == "fantasy"
    assert sequence == []


def test_build_engine_reads_mix(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("engine: mix\nsequence:\n  - poem\n  - fantasy\n")
    monkeypatch.setattr("trmnl.config.CONFIG_FILE", cfg)
    from trmnl.config import build_engine_from_config
    engine, name, sequence = build_engine_from_config()
    assert name == "mix"
    assert sequence == ["poem", "fantasy"]
    assert isinstance(engine, MixEngine)


def test_build_engine_malformed_file(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(": : invalid yaml : :")
    monkeypatch.setattr("trmnl.config.CONFIG_FILE", cfg)
    from trmnl.config import build_engine_from_config
    # Should not raise — falls back to mix
    engine, name, sequence = build_engine_from_config()
    assert name == "mix"


def test_build_engine_unknown_engine_name(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("engine: nonexistent\n")
    monkeypatch.setattr("trmnl.config.CONFIG_FILE", cfg)
    from trmnl.config import build_engine_from_config
    engine, name, sequence = build_engine_from_config()
    assert name == "mix"
```

- [ ] **Step 2: Run tests — expect failures**

```bash
uv run pytest tests/test_config.py -v
```

Expected: failures (CONFIG_FILE and build_engine_from_config don't exist yet).

- [ ] **Step 3: Update config.py**

Replace the full file:

```python
# src/trmnl/config.py
from __future__ import annotations
from dataclasses import dataclass
from xdg_base_dirs import xdg_cache_home
from pathlib import Path
from typing import TYPE_CHECKING
import logging
import yaml

if TYPE_CHECKING:
    from trmnl.carousel import ImageEngine
    from trmnl.engines.router import EngineRouter

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
    from trmnl.engines.registry import get_engine_registry
    registry = get_engine_registry()

    name = _DEFAULT_ENGINE
    sequence = list(_DEFAULT_SEQUENCE)

    try:
        if CONFIG_FILE.exists():
            with CONFIG_FILE.open() as f:
                data = yaml.safe_load(f) or {}
            name = data.get("engine", _DEFAULT_ENGINE)
            sequence = data.get("sequence", list(_DEFAULT_SEQUENCE))
    except Exception as e:
        logger.warning(f"config.yaml missing/unparseable ({e}), defaulting to mix")
        name = _DEFAULT_ENGINE
        sequence = list(_DEFAULT_SEQUENCE)

    if name != "mix" and name not in registry:
        logger.warning(f"Unknown engine '{name}' in config, defaulting to mix")
        name = _DEFAULT_ENGINE
        sequence = list(_DEFAULT_SEQUENCE)

    return _instantiate_engine(name, sequence, registry)


def _instantiate_engine(
    name: str, sequence: list[str], registry: dict[str, type]
) -> tuple[ImageEngine, str, list[str]]:
    if name == "mix":
        from trmnl.engines.router import MixEngine
        valid = [s for s in sequence if s in registry]
        if not valid:
            valid = list(registry.keys())
        engines = [registry[s]() for s in valid]
        return MixEngine(engines), "mix", valid
    else:
        return registry[name](), name, []


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
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
uv run pytest tests/test_config.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/trmnl/config.py tests/test_config.py
git commit -m "feat: replace default_engine with build_engine_from_config, add CONFIG_FILE"
```

---

## Task 6: FantasyEngine — prompts

**Files:**
- Create: `src/trmnl/engines/fantasy/prompts.py`

- [ ] **Step 1: Write prompts.py**

```python
# src/trmnl/engines/fantasy/prompts.py
from __future__ import annotations

STYLE_PREAMBLE = (
    "Albrecht Dürer woodcut engraving style, black and white only, "
    "fine crosshatching, stark contrast, dramatic chiaroscuro, no color, "
    "no gradients, 16th century German Renaissance printmaking aesthetic —"
)

PROMPTS: list[dict[str, str]] = [
    {"slug": "dragon_hoard", "prompt": "a dragon sleeping on its hoard of gold coins and jewels, curled up like a contented dog"},
    {"slug": "knight_forest", "prompt": "an armored knight on horseback pausing at the edge of a dark enchanted forest"},
    {"slug": "wizard_tower", "prompt": "a wizard's tower on a cliff edge at night, lit windows, storm clouds gathering"},
    {"slug": "sea_serpent", "prompt": "a sea serpent emerging from stormy waves to inspect a small fishing vessel"},
    {"slug": "gryphon_nest", "prompt": "a gryphon tending to its nest of eggs on a mountain peak"},
    {"slug": "dungeon_map", "prompt": "a detailed overhead map of a dungeon with traps, treasure rooms, and a dragon's lair"},
    {"slug": "alchemy_lab", "prompt": "an alchemist's laboratory cluttered with retorts, skulls, astrolabes, and bubbling flasks"},
    {"slug": "faerie_market", "prompt": "a midnight market under a bridge where fae creatures barter strange goods"},
    {"slug": "undead_army", "prompt": "a skeletal army marching through a ruined city at dusk, led by a lich king"},
    {"slug": "forest_witch", "prompt": "a witch's cottage deep in the woods, smoke rising from the chimney, herbs drying in the doorway"},
    {"slug": "siege_castle", "prompt": "a trebuchet launching stones at a castle gate while defenders pour boiling oil from battlements"},
    {"slug": "tavern_brawl", "prompt": "a chaotic tavern brawl, men thrown over tables, tankards flying, a bard still playing in the corner"},
    {"slug": "phoenix_rising", "prompt": "a phoenix erupting from ashes above a ruined temple, wings spread wide"},
    {"slug": "dwarven_forge", "prompt": "dwarven smiths hammering glowing metal in a vast underground forge lit by magma"},
    {"slug": "elven_council", "prompt": "an elven council meeting in a great hollow tree, ancient figures gesturing over a glowing map"},
    {"slug": "demon_summoning", "prompt": "a robed figure drawing a pentagram on a stone floor as a demon begins to materialize from smoke"},
    {"slug": "sea_voyage", "prompt": "a galleon with tattered sails navigating between enormous sea stacks in thick fog"},
    {"slug": "dragon_duel", "prompt": "two dragons locked in aerial combat above a burning village"},
    {"slug": "oracle_vision", "prompt": "a blind oracle seated at a smoking brazier, her face illuminated, pointing into darkness"},
    {"slug": "giant_chess", "prompt": "two giants playing chess with human knights as pieces in an ancient ruined hall"},
]
```

- [ ] **Step 2: Commit**

```bash
git add src/trmnl/engines/fantasy/prompts.py
git commit -m "feat: add fantasy engine prompt list (20 scenes)"
```

---

## Task 7: FantasyEngine

**Files:**
- Create: `src/trmnl/engines/fantasy/engine.py`
- Create: `tests/test_fantasy_engine.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_fantasy_engine.py
from __future__ import annotations
import pytest
from pathlib import Path


@pytest.mark.asyncio
async def test_fantasy_engine_empty_cache_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("trmnl.engines.fantasy.engine.FANTASY_DIR", tmp_path)
    # Re-import to pick up monkeypatched FANTASY_DIR
    import importlib
    import trmnl.engines.fantasy.engine as mod
    importlib.reload(mod)

    engine = mod.FantasyEngine()
    with pytest.raises(RuntimeError, match="background_process"):
        await engine.next()


@pytest.mark.asyncio
async def test_fantasy_engine_returns_bmp_path(tmp_path, monkeypatch):
    # Create a fake BMP in the cache dir
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
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
uv run pytest tests/test_fantasy_engine.py -v
```

Expected: ImportError (engine.py doesn't exist yet).

- [ ] **Step 3: Implement engine.py**

```python
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
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
uv run pytest tests/test_fantasy_engine.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Verify registry now resolves FantasyEngine**

```bash
uv run python -c "from trmnl.engines.registry import get_engine_registry; r = get_engine_registry(); print(r)"
```

Expected: dict with `poem` and `fantasy` keys.

- [ ] **Step 6: Commit**

```bash
git add src/trmnl/engines/fantasy/engine.py tests/test_fantasy_engine.py
git commit -m "feat: add FantasyEngine (cache-only, random BMP selection)"
```

---

## Task 8: Update app.py — lifespan, /ping, control router mount

**Files:**
- Modify: `src/trmnl/app.py`

- [ ] **Step 1: Replace app.py**

```python
# src/trmnl/app.py
from __future__ import annotations
from trmnl.config import settings, build_engine_from_config
from trmnl.logo import print_logo
from trmnl.carousel import Carousel, TRMNLImage
from trmnl.engines.router import EngineRouter
from fastapi import FastAPI, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine, name, sequence = build_engine_from_config()
    logger.info(f"Loaded engine config: engine={name} sequence={sequence}")

    router = EngineRouter(engine, name, sequence)
    carousel = Carousel(engine=router)

    try:
        await carousel.next()  # pre-load first image
    except Exception as e:
        logger.error(f"Error pre-loading carousel: {e}")

    app.state.router = router
    app.state.carousel = carousel

    print_logo()
    yield


app = FastAPI(lifespan=lifespan)

# Mount admin control router
from trmnl.control import router as control_router
app.include_router(control_router)


@app.get("/ping")
async def ping():
    return {"status": "ok"}


@app.get("/api/setup")
async def setup(request: Request, id: str = Header(None, alias="ID")):
    base_url = str(request.base_url).rstrip("/")
    logger.info(f"Setup request from device: {id}")
    return JSONResponse(
        content={
            "status": 200,
            "api_key": "local-server-key",
            "friendly_id": "LOCAL",
            "image_url": f"{base_url}/api/image/setup.bmp",
            "filename": "setup",
        }
    )


@app.get("/api/display")
async def display_config(
    request: Request,
    id: str = Header(None, alias="ID"),
    access_token: str = Header(None, alias="Access-Token"),
):
    logger.info(f"Display request from device: {id}, token: {access_token}")
    next_image: TRMNLImage = await request.app.state.carousel.next()
    return JSONResponse(
        content={
            "status": 0,
            "image_url": next_image.image_url,
            "filename": next_image.filename,
            "update_firmware": False,
            "firmware_url": None,
            "refresh_rate": settings.refresh_interval,
            "reset_firmware": False,
        }
    )


@app.get("/api/image/{filename}")
async def serve_image(filename: str):
    logger.info("Serving image to device.")
    current_image = await app.state.carousel.current()
    assert filename == current_image.filename + ".bmp", "Filename mismatch!"
    return FileResponse(current_image.path, media_type="image/bmp")


@app.post("/api/log")
async def log_device_stats(request: Request):
    logger.info("Received device log.")
    payload = await request.json()
    logger.info(f"DEVICE LOG: {payload}")
    return {"status": "ok"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(request: Request, path: str):
    logger.info(f"CATCH-ALL: {request.method} /{path}")
    return {"caught": path}
```

- [ ] **Step 2: Verify server starts (no crash)**

```bash
uv run python -c "from trmnl.app import app; print('app loaded ok')"
```

Expected: `app loaded ok`

- [ ] **Step 3: Commit**

```bash
git add src/trmnl/app.py
git commit -m "feat: update lifespan to use EngineRouter + build_engine_from_config; add /ping"
```

---

## Task 9: Admin Control API

**Files:**
- Create: `src/trmnl/control.py`
- Create: `tests/test_control_api.py`

- [ ] **Step 1: Write failing tests**

```python
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
    assert "bogus" in resp.json()["error"]


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
```

- [ ] **Step 2: Run tests — expect import errors**

```bash
uv run pytest tests/test_control_api.py -v
```

Expected: failures (control.py doesn't exist).

- [ ] **Step 3: Implement control.py**

```python
# src/trmnl/control.py
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel
from fastapi import APIRouter, Request, HTTPException
import yaml
import logging

from trmnl.config import CONFIG_FILE
from trmnl.engines.registry import get_engine_registry
from trmnl.engines.router import EngineRouter, MixEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/control")


class EngineRequest(BaseModel):
    engine: str
    sequence: list[str] | None = None


@router.get("/status")
async def status(request: Request):
    eng_router: EngineRouter = request.app.state.router
    last = eng_router.last_served.name if eng_router.last_served else None
    logger.info("Control: GET /status")
    return {
        "engine": eng_router.active_name,
        "sequence": eng_router.active_sequence,
        "last_served": last,
    }


@router.get("/engines")
async def list_engines():
    logger.info("Control: GET /engines")
    return {"engines": list(get_engine_registry().keys())}


@router.post("/engine")
async def set_engine(request: Request, body: EngineRequest):
    registry = get_engine_registry()

    if body.engine != "mix" and body.engine not in registry:
        valid = ", ".join(registry.keys())
        raise HTTPException(400, detail=f"Unknown engine '{body.engine}'. Valid engines: {valid}")

    sequence = body.sequence or list(registry.keys())
    engine_obj, name, resolved_seq = _build(body.engine, sequence, registry)

    eng_router: EngineRouter = request.app.state.router
    eng_router.set_engine(engine_obj, name, resolved_seq)

    _write_config(name, resolved_seq)
    logger.info(f"Control: POST /engine → {name} {resolved_seq}")
    return {"ok": True, "engine": name, "sequence": resolved_seq}


@router.post("/next")
async def advance_next(request: Request):
    carousel = request.app.state.carousel
    image = await carousel.next()
    logger.info(f"Control: POST /next → {image.filename}")
    return {"ok": True, "image": image.filename + ".bmp"}


@router.post("/reload")
async def reload_config(request: Request):
    from trmnl.config import build_engine_from_config
    try:
        engine_obj, name, sequence = build_engine_from_config()
    except Exception as e:
        raise HTTPException(500, detail=f"Failed to reload config: {e}")

    eng_router: EngineRouter = request.app.state.router
    eng_router.set_engine(engine_obj, name, sequence)
    logger.info(f"Control: POST /reload → {name} {sequence}")
    return {"ok": True, "engine": name, "sequence": sequence}


def _build(name: str, sequence: list[str], registry: dict) -> tuple:
    if name == "mix":
        valid = [s for s in sequence if s in registry]
        if not valid:
            valid = list(registry.keys())
        engines = [registry[s]() for s in valid]
        return MixEngine(engines), "mix", valid
    else:
        return registry[name](), name, []


def _write_config(name: str, sequence: list[str]) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w") as f:
        yaml.dump({"engine": name, "sequence": sequence}, f)
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
uv run pytest tests/test_control_api.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Run full suite**

```bash
uv run pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/trmnl/control.py tests/test_control_api.py
git commit -m "feat: add admin control API (/api/control/*)"
```

---

## Task 10: trmnl-ctl CLI

**Files:**
- Create: `src/trmnl/cli.py`

- [ ] **Step 1: Implement cli.py**

```python
# src/trmnl/cli.py
from __future__ import annotations
import argparse
import os
import sys

import httpx

SERVER_URL = os.environ.get("TRMNL_SERVER_URL", "http://caruana:8070")


def _get(path: str) -> dict:
    try:
        resp = httpx.get(f"{SERVER_URL}{path}", timeout=5.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        print(f"Could not connect to TRMNL server at {SERVER_URL}. Is the service running?")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"Error {e.response.status_code}: {e.response.json().get('error', str(e))}")
        sys.exit(1)


def _post(path: str, body: dict) -> dict:
    try:
        resp = httpx.post(f"{SERVER_URL}{path}", json=body, timeout=5.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        print(f"Could not connect to TRMNL server at {SERVER_URL}. Is the service running?")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"Error {e.response.status_code}: {e.response.json().get('error', str(e))}")
        sys.exit(1)


def cmd_status(_args: argparse.Namespace) -> None:
    data = _get("/api/control/status")
    print(f"Engine:      {data['engine']}")
    if data.get("sequence"):
        print(f"Sequence:    {' → '.join(data['sequence'])}")
    print(f"Last served: {data['last_served'] or '(none)'}")


def cmd_list(_args: argparse.Namespace) -> None:
    data = _get("/api/control/engines")
    print("Available engines:")
    for name in data["engines"]:
        print(f"  {name}")


def cmd_engine(args: argparse.Namespace) -> None:
    body: dict = {"engine": args.name}
    if args.name == "mix":
        if args.sequence:
            body["sequence"] = args.sequence
        else:
            body["sequence"] = _get("/api/control/engines")["engines"]
    data = _post("/api/control/engine", body)
    print(f"OK — engine: {data['engine']}")
    if data.get("sequence"):
        print(f"Sequence: {' → '.join(data['sequence'])}")


def cmd_next(_args: argparse.Namespace) -> None:
    data = _post("/api/control/next", {})
    print(f"Advanced — next image: {data['image']}")


def cmd_reload(_args: argparse.Namespace) -> None:
    data = _post("/api/control/reload", {})
    print(f"Reloaded — engine: {data['engine']}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="trmnl-ctl", description="TRMNL remote control")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show current engine and last served image")
    sub.add_parser("list", help="List available engines")
    sub.add_parser("next", help="Force carousel to advance")
    sub.add_parser("reload", help="Re-read config.yaml and apply without restart")

    p_engine = sub.add_parser("engine", help="Switch active engine")
    p_engine.add_argument("name", help="Engine name: poem, fantasy, or mix")
    p_engine.add_argument(
        "--sequence",
        nargs="+",
        metavar="ENGINE",
        help="Ordered sequence for mix mode, e.g. --sequence poem poem fantasy",
    )

    args = parser.parse_args()
    {
        "status": cmd_status,
        "list": cmd_list,
        "engine": cmd_engine,
        "next": cmd_next,
        "reload": cmd_reload,
    }[args.command](args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify entry point is wired**

```bash
uv run trmnl-ctl --help
```

Expected: usage message with subcommands listed.

- [ ] **Step 3: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add src/trmnl/cli.py
git commit -m "feat: add trmnl-ctl CLI (status, list, engine, next, reload)"
```

---

## Task 11: test_image_gen.py — style validation script

**Files:**
- Create: `scripts/test_image_gen.py`

- [ ] **Step 1: Create the script**

```python
#!/usr/bin/env python3
"""
Generate BMP variants of one scene with different style prompts.
Run: uv run python scripts/test_image_gen.py
Output: <project_root>/test_output/test_0.bmp … test_5.bmp
"""
from __future__ import annotations
import asyncio
import base64
import io
from pathlib import Path

from PIL import Image

OUTPUT_DIR = Path(__file__).parent.parent / "test_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCENE = "a dragon sleeping on its hoard of gold coins and jewels, curled up like a contented dog"

STYLE_VARIANTS = [
    (
        "durer",
        "Albrecht Dürer woodcut engraving style, black and white only, fine crosshatching, "
        "stark contrast, dramatic chiaroscuro, no color, no gradients, "
        "16th century German Renaissance printmaking aesthetic —",
    ),
    (
        "dore",
        "Gustave Doré engraving style, black and white only, fine crosshatching, "
        "high drama, detailed linework, no color, no gradients —",
    ),
    (
        "linocut",
        "linocut print, bold black and white, high contrast, simplified shapes, "
        "minimal detail, stark shadows —",
    ),
    (
        "medieval_manuscript",
        "medieval manuscript ink illustration, black ink on parchment, "
        "detailed pen linework, no color, flat areas —",
    ),
    (
        "pen_ink",
        "pen and ink illustration, black and white, architectural fine hatching lines, "
        "no color, no gradients —",
    ),
    (
        "woodblock",
        "Japanese woodblock print aesthetic, black and white only, bold outlines, "
        "flat areas, no gradients, stark —",
    ),
]


async def generate_variant(index: int, label: str, preamble: str) -> Path:
    from conduit.core.model.model_async import ModelAsync

    model = ModelAsync("dall-e-3")
    prompt = f"{preamble} {SCENE}"
    response = await model.image.generate(
        prompt_str=prompt,
        size="1792x1024",
        quality="hd",
        style="natural",
        response_format="b64_json",
    )
    images = response.message.images
    if not images:
        raise RuntimeError(f"Variant {index} ({label}): empty response from API")

    image_data = base64.b64decode(images[0].b64_json)
    image = Image.open(io.BytesIO(image_data))
    image = image.resize((800, 480))
    bmp = image.convert("1")
    output_path = OUTPUT_DIR / f"test_{index}_{label}.bmp"
    bmp.save(output_path)
    return output_path


async def main() -> None:
    print(f"Generating {len(STYLE_VARIANTS)} variants concurrently...")
    tasks = [
        generate_variant(i, label, preamble)
        for i, (label, preamble) in enumerate(STYLE_VARIANTS)
    ]
    paths = await asyncio.gather(*tasks)
    print("\nOutput files:")
    for path in paths:
        print(f"  {path}")
    print(f"\nOpen all: open {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Add test_output/ to .gitignore**

```bash
echo "test_output/" >> .gitignore
git add .gitignore
```

- [ ] **Step 3: Commit**

```bash
git add scripts/test_image_gen.py .gitignore
git commit -m "feat: add test_image_gen.py style validation script"
```

---

## ⚠️ HITL STOP 1: Run style test and eyeball BMPs

**Agent must stop here. Do not proceed until human approves.**

```
HUMAN ACTION REQUIRED:
  1. Run: uv run python scripts/test_image_gen.py
     (This calls DALL-E 3 × 6 — costs ~$0.48 at hd quality)
  2. Open outputs: open test_output/
  3. Review all 6 BMPs on screen. They are 800×480 1-bit black and white.
  4. Identify which style label looks best on e-ink.
  5. Report back: which style(s) looked good? Any that were unusable?
  6. Confirm: is "durer" the right default for STYLE_PREAMBLE in prompts.py?
     (Update prompts.py if a different variant won.)

Only continue once you have confirmed the style.
```

---

## Task 12: background_process.py

**Files:**
- Create: `src/trmnl/engines/fantasy/background_process.py`

- [ ] **Step 1: Implement background_process.py**

```python
# src/trmnl/engines/fantasy/background_process.py
"""
Idempotent image generator for the FantasyEngine cache.
Run locally (not on caruana) — requires OPENAI_API_KEY in environment.

Usage:
    uv run python src/trmnl/engines/fantasy/background_process.py

Costs ~$0.08 per image (DALL-E 3 hd quality). Skips already-cached slugs.
Add new entries to PROMPTS and re-run to extend the cache.
"""
from __future__ import annotations
import asyncio
import base64
import io
import logging
from pathlib import Path

from PIL import Image
from rich.console import Console

from trmnl.config import settings
from trmnl.engines.fantasy.prompts import STYLE_PREAMBLE, PROMPTS

console = Console()
logger = logging.getLogger(__name__)

FANTASY_DIR = settings.paths["CACHE_DIR"] / "fantasy"
FANTASY_DIR.mkdir(parents=True, exist_ok=True)


async def _generate_one(slug: str, prompt: str) -> bool:
    """Generate and save one BMP. Returns True on success."""
    from conduit.core.model.model_async import ModelAsync

    output_path = FANTASY_DIR / f"fantasy_{slug}.bmp"
    tmp_path = FANTASY_DIR / f"fantasy_{slug}.bmp.tmp"
    full_prompt = f"{STYLE_PREAMBLE} {prompt}"

    try:
        model = ModelAsync("dall-e-3")
        response = await model.image.generate(
            prompt_str=full_prompt,
            size="1792x1024",
            quality="hd",
            style="natural",
            response_format="b64_json",
        )
    except Exception as e:
        console.print(f"[red]Failed {slug}[/red]: {e}")
        return False

    images = response.message.images
    if not images:
        console.print(f"[red]Failed {slug}[/red]: empty response from API")
        return False

    image_data = base64.b64decode(images[0].b64_json)
    image = Image.open(io.BytesIO(image_data))
    image = image.resize((800, 480))
    bmp = image.convert("1")
    bmp.save(tmp_path)
    tmp_path.rename(output_path)

    size = output_path.stat().st_size
    console.print(f"[green]Generated {slug}[/green] → {output_path.name} ({size} bytes)")
    return True


async def run() -> None:
    n_generated = n_skipped = n_failed = 0

    for entry in PROMPTS:
        slug = entry["slug"]
        output_path = FANTASY_DIR / f"fantasy_{slug}.bmp"

        if output_path.exists():
            console.print(f"[blue]Skipping {slug} (already cached)[/blue]")
            n_skipped += 1
            continue

        success = await _generate_one(slug, entry["prompt"])
        if success:
            n_generated += 1
        else:
            n_failed += 1

    console.print(
        f"\nDone: [green]{n_generated} generated[/green], "
        f"[blue]{n_skipped} skipped[/blue], "
        f"[red]{n_failed} failed[/red]"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(run())
```

- [ ] **Step 2: Commit**

```bash
git add src/trmnl/engines/fantasy/background_process.py
git commit -m "feat: add fantasy engine background process (idempotent BMP generator)"
```

---

## ⚠️ HITL STOP 2: Run background_process.py to generate image cache

**Agent must stop here. Do not proceed until human approves.**

```
HUMAN ACTION REQUIRED:
  1. This script will call DALL-E 3 for each of the 20 PROMPTS entries.
     Estimated cost: ~$1.60 (20 × $0.08 at hd quality).
  2. Run: uv run python src/trmnl/engines/fantasy/background_process.py
  3. Watch the output. Failed slugs can be recovered by re-running.
  4. Verify cache: ls ~/.cache/trmnl/fantasy/ | wc -l  (should show ~20 files)
  5. Spot-check a few BMPs: open ~/.cache/trmnl/fantasy/fantasy_dragon_hoard.bmp
  6. Report back: how many generated, any failures to fix?

Only continue once cache is populated to your satisfaction.
```

---

## Task 13: deploy.sh

**Files:**
- Create: `scripts/deploy.sh`

- [ ] **Step 1: Create deploy.sh**

```bash
#!/usr/bin/env bash
# Deploy trmnl code changes to caruana.
#
# Usage:
#   bash scripts/deploy.sh
#
# Requires: GITHUB_PERSONAL_TOKEN env var (for git pull auth on caruana)

set -euo pipefail

LOCAL_REPO="$HOME/Brian_Code/trmnl-project"
REMOTE_REPO="/home/bianders/Brian_Code/trmnl-project"
GITHUB_REPO="acesanderson/trmnl-project"
HOST="caruana"
SERVICE="trmnl"
PORT=8070

echo "==> pushing to origin..."
git -C "$LOCAL_REPO" push

echo "==> [$HOST] pulling code..."
ssh "$HOST" "git -C $REMOTE_REPO pull --ff-only https://${GITHUB_PERSONAL_TOKEN}@github.com/${GITHUB_REPO}.git"

echo "==> [$HOST] syncing dependencies..."
ssh "$HOST" "cd $REMOTE_REPO && uv sync"

echo "==> [$HOST] restarting $SERVICE..."
ssh "$HOST" "sudo systemctl restart $SERVICE"

echo -n "==> [$HOST] waiting for $SERVICE on :$PORT ... "
for i in $(seq 1 20); do
    if ssh "$HOST" "curl -sf http://localhost:$PORT/ping" > /dev/null 2>&1; then
        echo "up"
        exit 0
    fi
    if [[ $i -eq 20 ]]; then
        echo "TIMEOUT after 20s"
        echo "    Run: ssh $HOST 'journalctl -u $SERVICE -n 30' for details"
        exit 1
    fi
    sleep 1
done
```

- [ ] **Step 2: Make executable and verify GitHub repo name**

The `GITHUB_REPO` variable in `deploy.sh` is set to `acesanderson/trmnl-project`. Verify this matches the actual remote:

```bash
git remote get-url origin
```

Update `GITHUB_REPO` in `deploy.sh` if the repo name differs.

- [ ] **Step 3: Commit**

```bash
git add scripts/deploy.sh
chmod +x scripts/deploy.sh
git commit -m "feat: add deploy.sh (push → pull caruana → uv sync → systemctl restart)"
```

---

## ⚠️ HITL STOP 3: Daemonize trmnl on caruana

**Agent must stop here. This step requires manual SSH work on caruana.**

```
HUMAN ACTION REQUIRED — run these commands on caruana:

1. Confirm uv path:
   ssh caruana "which uv"
   (Expected: /home/bianders/.local/bin/uv — update ExecStart below if different)

2. Create the EnvironmentFile (may be empty for now):
   ssh caruana "mkdir -p ~/.config/trmnl && touch ~/.config/trmnl/env"

3. Create the systemd unit:
   ssh caruana "sudo tee /etc/systemd/system/trmnl.service" << 'EOF'
   [Unit]
   Description=TRMNL local server

   [Service]
   User=bianders
   WorkingDirectory=/home/bianders/Brian_Code/trmnl-project
   ExecStart=/home/bianders/.local/bin/uv run trmnl
   Restart=on-failure
   EnvironmentFile=/home/bianders/.config/trmnl/env

   [Install]
   WantedBy=multi-user.target
   EOF

4. Enable and reload:
   ssh caruana "sudo systemctl daemon-reload && sudo systemctl enable trmnl"

5. Confirm the project is cloned on caruana at the right path:
   ssh caruana "ls /home/bianders/Brian_Code/trmnl-project/pyproject.toml"

6. Run uv sync on caruana manually first:
   ssh caruana "cd /home/bianders/Brian_Code/trmnl-project && uv sync"

7. Start the service manually to verify it works before relying on deploy.sh:
   ssh caruana "sudo systemctl start trmnl"
   ssh caruana "systemctl status trmnl"
   ssh caruana "curl -s http://localhost:8070/ping"
   (Expected: {"status":"ok"})

8. If it fails, check logs:
   ssh caruana "journalctl -u trmnl -n 50"

Report back once the service starts successfully.
```

---

## ⚠️ HITL STOP 4: First deploy and device verification

**Agent must stop here.**

```
HUMAN ACTION REQUIRED:

1. Run the deploy script from your local machine:
   bash scripts/deploy.sh

   Expected output:
     ==> pushing to origin...
     ==> [caruana] pulling code...
     ==> [caruana] syncing dependencies...
     ==> [caruana] restarting trmnl...
     ==> [caruana] waiting for trmnl on :8070 ... up

2. Verify the control layer works from your local machine:
   trmnl-ctl status
   trmnl-ctl list
   trmnl-ctl engine mix --sequence poem fantasy
   trmnl-ctl status

3. Wait for the TRMNL device to poll (up to 60 seconds per refresh_interval).
   Confirm the device displays an image.

4. Switch to fantasy-only and wait for next poll:
   trmnl-ctl engine fantasy
   (Device should show a fantasy BMP on next poll)

5. Switch to mix and confirm alternation across polls:
   trmnl-ctl engine mix

Report any issues. The deploy script is idempotent — run it again after any fixes.
```

---

## Self-Review

**Spec coverage check:**
- ✅ FantasyEngine (tasks 6–7)
- ✅ STYLE_PREAMBLE in prompts.py (task 6)
- ✅ background_process with atomic write + skip logic (task 12)
- ✅ ENGINE_REGISTRY (task 3)
- ✅ MixEngine round-robin + ValueError on empty (task 4)
- ✅ EngineRouter hot-swap + last_served tracking (task 4)
- ✅ build_engine_from_config() with fallback (task 5)
- ✅ FANTASY_DIR.mkdir at module load (task 7)
- ✅ /ping endpoint (task 8)
- ✅ lifespan updated to EngineRouter (task 8)
- ✅ All 5 control endpoints (task 9)
- ✅ HTTP 400 on unknown engine (task 9)
- ✅ Config written after successful rebuild only (task 9)
- ✅ trmnl-ctl with all 5 commands (task 10)
- ✅ Connection error → clean message + exit 1 (task 10)
- ✅ TRMNL_SERVER_URL env var (task 10)
- ✅ test_image_gen.py with concurrent generation (task 11)
- ✅ deploy.sh with poll loop + timeout hint (task 13)
- ✅ All 4 HITL stops called out
- ✅ 18 acceptance criteria covered across tasks 3–13

**Placeholder scan:** No TBDs, TODOs, or vague steps found.

**Type consistency:** `EngineRouter`, `MixEngine` defined in task 4 — used consistently by name in tasks 5, 8, 9, 10. `get_engine_registry()` returns `dict[str, type[ImageEngine]]` — consumed the same way in tasks 3, 5, 9. `build_engine_from_config()` returns `tuple[ImageEngine, str, list[str]]` — unpacked as `engine, name, sequence` consistently in tasks 5, 8, 9.
