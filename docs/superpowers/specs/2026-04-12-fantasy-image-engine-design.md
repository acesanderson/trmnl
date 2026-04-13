# Fantasy Image Engine & Engine Control Layer — Design Spec

**Date:** 2026-04-12
**Status:** Approved

---

## Overview

Two parallel workstreams:

**1. FantasyEngine** — a new `ImageEngine` that serves AI-generated Dürer-style fantasy illustrations. Images are generated once via DALL-E 3, converted to 800×480 1-bit BMP, and cached permanently. Zero API calls at runtime.

**2. Engine Control Layer** — a runtime control system: a YAML config file, an `EngineRouter`/`MixEngine` abstraction, admin HTTP endpoints, and a `trmnl-ctl` CLI that lets any client device switch engines or mix without restarting the server.

A testing script validates image quality before committing to a full prompt list. A deploy script and systemd service enable a fast local→caruana inner loop.

---

## File Layout

All `scripts/` paths are at the project root (same level as `src/`, `pyproject.toml`).

```
src/trmnl/
    app.py                      # +GET /ping, +APIRouter for /api/control/*
    config.py                   # default_engine() replaced by build_engine_from_config()
    cli.py                      # trmnl-ctl entry point (httpx-based)
    engines/
        registry.py             # ENGINE_REGISTRY dict
        router.py               # EngineRouter + MixEngine
        poems/                  # (unchanged)
        fantasy/
            __init__.py         # empty
            engine.py           # FantasyEngine
            prompts.py          # STYLE_PREAMBLE + PROMPTS
            background_process.py

scripts/
    test_image_gen.py
    deploy.sh

~/.config/trmnl/
    config.yaml                 # persisted engine selection (written by server, read on startup)
    env                         # systemd EnvironmentFile (may be empty)
```

Cache dir: `~/.cache/trmnl/fantasy/` (XDG, same pattern as poems).

---

## Config File (`~/.config/trmnl/config.yaml`)

Written by the server when a control command is applied. Read by the server on startup.

```yaml
engine: mix          # "poem", "fantasy", or "mix"
sequence:
  - poem
  - fantasy
```

`sequence` is only meaningful when `engine: mix`. When `engine` is a single engine name, `sequence` is ignored.

**On startup:** if the file is missing or unparseable, the server falls back to `engine: mix` with all engines in `ENGINE_REGISTRY` insertion order, and logs a warning. It does not crash.

**`config.py` change:** `default_engine()` is removed. A new `build_engine_from_config() -> ImageEngine` function reads `~/.config/trmnl/config.yaml` and returns the appropriate engine (single or `MixEngine`). Called from `lifespan` in `app.py`.

---

## Engine Registry (`engines/registry.py`)

```python
ENGINE_REGISTRY: dict[str, type[ImageEngine]] = {
    "poem": PoemEngine,
    "fantasy": FantasyEngine,
}
```

Single source of truth for valid engine names. Used by `build_engine_from_config()`, admin endpoints, and CLI validation. Adding a new engine requires only adding it here.

---

## EngineRouter (`engines/router.py`)

A thin `ImageEngine` wrapper stored in `app.state.router`. The `Carousel` holds the router, never the engine directly. Allows hot-swapping the active engine without touching the Carousel.

```python
class EngineRouter:
    def __init__(self, engine: ImageEngine):
        self.active_engine: ImageEngine = engine
        self.active_name: str = ""        # set by build_engine_from_config()
        self.active_sequence: list[str] = []  # set by build_engine_from_config()
        self.last_served: Path | None = None

    async def next(self) -> Path:
        path = await self.active_engine.next()
        self.last_served = path
        return path

    def set_engine(self, engine: ImageEngine, name: str, sequence: list[str]) -> None:
        self.active_engine = engine
        self.active_name = name
        self.active_sequence = sequence
        # log: INFO — Engine switched to {name} (sequence: {sequence})
```

`set_engine()` is not concurrency-safe. This is acceptable — single-user personal device, no concurrent control clients.

---

## MixEngine (`engines/router.py`)

Defined in the same file as `EngineRouter`.

```python
class MixEngine:
    def __init__(self, engines: list[ImageEngine]):
        if not engines:
            raise ValueError("MixEngine requires at least one engine")
        self.engines = engines
        self._index = 0

    async def next(self) -> Path:
        engine = self.engines[self._index % len(self.engines)]
        self._index = (self._index + 1) % len(self.engines)
        # log: DEBUG — MixEngine: selected engine {index}, advancing to {next_index}
        return await engine.next()
```

`_index` resets to 0 on server restart — this is intentional. The sequence resumes from the beginning on each restart.

---

## Admin API (`/api/control/*`)

Mounted as a FastAPI `APIRouter` with prefix `/api/control`. **No authentication** — local network only. A subagent must not add auth.

All request bodies are JSON. All responses are JSON.

### `GET /api/control/status`
Returns current engine name, active sequence, and last served filename.

Response:
```json
{
  "engine": "mix",
  "sequence": ["poem", "fantasy"],
  "last_served": "fantasy_dragon_hoard.bmp"
}
```
`last_served` is `null` if no image has been served since startup.

### `GET /api/control/engines`
Returns list of registered engine name strings.
```json
{"engines": ["poem", "fantasy"]}
```

### `POST /api/control/engine`
Switches the active engine. Rebuilds the engine, hot-swaps into `EngineRouter`, then writes `config.yaml`. Config is only written after successful engine rebuild.

Request body:
```json
{"engine": "mix", "sequence": ["poem", "fantasy"]}
```
`sequence` is required when `engine` is `"mix"`, ignored otherwise.

Returns HTTP 400 if `engine` is not a key in `ENGINE_REGISTRY`, with body:
```json
{"error": "Unknown engine 'foo'. Valid engines: poem, fantasy"}
```
Returns HTTP 200 on success:
```json
{"ok": true, "engine": "mix", "sequence": ["poem", "fantasy"]}
```

### `POST /api/control/next`
Advances the carousel (calls `carousel.next()`). The next device poll will receive the new image. Does not push to the device — the device polls on its own schedule.

Returns HTTP 200:
```json
{"ok": true, "image": "abc123.bmp"}
```

### `POST /api/control/reload`
Re-reads `~/.config/trmnl/config.yaml` from disk and applies it. Used when the file is edited manually on caruana.

Returns HTTP 200 on success, HTTP 500 if file is missing or unparseable (with error message).

---

## `trmnl-ctl` CLI (`src/trmnl/cli.py`)

Entry point: `trmnl-ctl` (added to `pyproject.toml` `[project.scripts]`).

HTTP client: `httpx` (synchronous). `httpx` must be added to `pyproject.toml` dependencies.

Target URL: `TRMNL_SERVER_URL` env var, default `http://caruana:8070`. All commands use this base URL.

On connection failure: print `"Could not connect to TRMNL server at {url}. Is the service running?"` and exit 1. Never show a Python traceback to the user.

**Commands:**

```bash
trmnl-ctl status
# Prints: engine, sequence, last_served

trmnl-ctl list
# Prints available engine names from ENGINE_REGISTRY

trmnl-ctl engine poem
trmnl-ctl engine fantasy
trmnl-ctl engine mix
trmnl-ctl engine mix --sequence poem poem fantasy
# --sequence is required when engine is mix with a non-default order
# Default mix sequence: all engines in ENGINE_REGISTRY insertion order

trmnl-ctl next
# Forces carousel to advance; prints new image filename

trmnl-ctl reload
# Tells server to re-read config.yaml
```

`trmnl-ctl` does not write to the local filesystem. All persistence flows through the server API.

---

## Image Generation

**Model:** `dall-e-3` via `conduit.core.model.model_async.ModelAsync`

**Parameters:**
- `size="1792x1024"` — DALL-E 3's only landscape option (1.75:1, resizes cleanly to 800×480)
- `quality="hd"`
- `style="natural"` — avoids oversaturation, better for print-style compositions
- `response_format="b64_json"`

**Call pattern:**
```python
model = ModelAsync("dall-e-3")
response = await model.image.generate(
    prompt_str=f"{STYLE_PREAMBLE} {entry['prompt']}",
    size="1792x1024",
    quality="hd",
    style="natural",
    response_format="b64_json",
)
```

**Post-processing:** `response.message.images[0].b64_json` → `base64.b64decode` → `Image.open(BytesIO(...))` → `image.resize((800, 480))` → `image.convert("1")` → `save(output_path)`. Done inline with Pillow — `image_to_bmp()` is not used (requires file path input, not bytes).

**Write atomically:** write to `fantasy_{slug}.bmp.tmp`, then `Path.rename()` to `fantasy_{slug}.bmp` on success. Prevents corrupt BMPs if interrupted mid-write.

---

## Style Preamble

Defined as `STYLE_PREAMBLE` in `prompts.py`. Prepended to every prompt at generation time — not stored in `PROMPTS` entries.

```python
STYLE_PREAMBLE = (
    "Albrecht Dürer woodcut engraving style, black and white only, "
    "fine crosshatching, stark contrast, dramatic chiaroscuro, no color, "
    "no gradients, 16th century German Renaissance printmaking aesthetic —"
)
```

If `STYLE_PREAMBLE` changes, cached BMPs are not invalidated automatically. Delete `~/.cache/trmnl/fantasy/` manually and re-run the background process.

---

## Prompts List (`prompts.py`)

```python
PROMPTS = [
    {"slug": "dragon_hoard", "prompt": "a dragon sleeping on its hoard of gold coins and jewels, curled up like a contented dog"},
    # 20-30 total entries
]
```

**`prompt`:** scene description only — no style guidance. Full prompt is `f"{STYLE_PREAMBLE} {entry['prompt']}"`, assembled in `background_process.py`.

**`slug`:** stable, filesystem-safe identifier (lowercase, underscores only). Cache filename: `fantasy_{slug}.bmp`. Never change a slug after its BMP has been generated — it will appear as uncached on the next run.

Adding a new entry and re-running the background script generates the missing BMP — the list is the queue.

---

## Background Process (`background_process.py`)

Idempotent — safe to re-run at any time. Run locally (not on caruana) — `OPENAI_API_KEY` is in the local environment.

```
for each entry in PROMPTS:
    if fantasy_{slug}.bmp exists → log skip, continue
    else:
        call ModelAsync("dall-e-3").image.generate(...)
        if exception → log slug + message, continue
        if response.message.images is None or empty → log slug + "empty response", continue
        write to fantasy_{slug}.bmp.tmp → rename to fantasy_{slug}.bmp
        log: filename + file size in bytes

print summary: N generated, M skipped, K failed
```

No concurrency. No retry. Rich console output, same pattern as poems.

---

## FantasyEngine (`engine.py`)

At module load: `FANTASY_DIR.mkdir(parents=True, exist_ok=True)`.

At instantiation: log at INFO the count of cached BMPs.

**`next()`:**
1. Glob `FANTASY_DIR / "*.bmp"`
2. If empty → log ERROR, raise `RuntimeError("No fantasy images cached. Run background_process.py first.")`
3. `random.choice(bmp_files)` — pure random with replacement (same image may appear consecutively; intentional)
4. Log at INFO: selected filename
5. Return `Path`

No API calls. No state.

---

## Testing Script (`scripts/test_image_gen.py`)

Generates 4-6 BMP variants of "dragon sleeping on its hoard" with different prompt phrasings and/or style preamble variations (e.g. Dürer vs. Gustave Doré). All calls run concurrently via `asyncio.gather`. Output dir: `Path(__file__).parent.parent / "test_output"` (anchored to project root). Saves as `test_0.bmp`, `test_1.bmp`, etc. Prints absolute paths to stdout.

---

## Deploy & Daemonization

### `scripts/deploy.sh`

```
1. git push local branch
2. SSH caruana → git pull --ff-only (with GITHUB_PERSONAL_TOKEN)
3. SSH caruana → uv sync
4. SSH caruana → sudo systemctl restart trmnl
5. Poll http://caruana:8070/ping every 1s, up to 20s
   → exit 0 on success
   → exit 1 on timeout, print "journalctl -u trmnl -n 30" hint
```

If `git pull --ff-only` fails, script aborts. Service stays on previous version.

### Systemd Unit (created once by hand on caruana)

`/etc/systemd/system/trmnl.service`:
```ini
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
```

`/home/bianders/.config/trmnl/env` may be empty but must exist. Add API keys here if future engines need them at runtime.

Enable: `sudo systemctl enable trmnl && sudo systemctl daemon-reload`

**Confirm `uv` path on caruana with `which uv` before writing the unit file.**

### `/ping` endpoint

```python
@app.get("/ping")
async def ping():
    return {"status": "ok"}
```

---

## Observability

### Engine (systemd service — `journalctl -u trmnl -f`)

- **Startup:** `INFO — Loaded engine config: engine={name} sequence={sequence}`
- **Config fallback:** `WARNING — config.yaml missing/unparseable, defaulting to mix`
- **Engine hot-swap:** `INFO — Engine switched to {name} (sequence: {sequence})`
- **MixEngine step:** `DEBUG — MixEngine: index {i} → {engine_name}`
- **FantasyEngine init:** `INFO — FantasyEngine initialized with {n} cached images`
- **FantasyEngine serve:** `INFO — FantasyEngine serving: {filename}`
- **FantasyEngine empty cache:** `ERROR — FantasyEngine: no images in cache`
- **Admin endpoint hit:** `INFO — Control: {METHOD} {path} {status_code}`

### Background Process (local stdout)

- Per skip: `Skipping {slug} (already cached)`
- Per generation: `Generated {slug} → {path} ({size} bytes)`
- Per failure: `Failed {slug}: {exception}`
- Final: `Done: {n} generated, {m} skipped, {k} failed`

---

## Acceptance Criteria

All must be true before implementation is complete:

**FantasyEngine:**
1. `background_process.py` with `PROMPTS = [{"slug": "dragon_hoard", ...}]` produces `~/.cache/trmnl/fantasy/fantasy_dragon_hoard.bmp`.
2. Re-running `background_process.py` does not regenerate `fantasy_dragon_hoard.bmp` (mtime unchanged).
3. `fantasy_dragon_hoard.bmp` is exactly 800×480 pixels, 1-bit depth, under 90 KB.
4. `FantasyEngine.next()` returns a `.bmp` `Path` when cache is non-empty.
5. `FantasyEngine.next()` raises `RuntimeError` containing "background_process" when cache is empty.

**Control layer:**
6. `GET /api/control/engines` returns a list containing at least `"poem"` and `"fantasy"`.
7. `POST /api/control/engine {"engine": "fantasy"}` → subsequent device polls are served by `FantasyEngine`.
8. `POST /api/control/engine {"engine": "mix", "sequence": ["poem", "fantasy"]}` → device polls alternate poem/fantasy strictly.
9. `POST /api/control/engine {"engine": "bogus"}` → HTTP 400 with error message naming valid engines.
10. `trmnl-ctl status` prints current engine name and last served filename.
11. `trmnl-ctl next` causes the carousel to advance; `status` shows a new `last_served` value.
12. `trmnl-ctl engine mix --sequence poem poem fantasy` → server follows that 3-step sequence cyclically.
13. Server restart with `config.yaml` containing `engine: fantasy` → service starts in fantasy-only mode.
14. `trmnl-ctl` connection failure → clean error message, exit 1, no Python traceback.

**Infrastructure:**
15. `GET /ping` returns HTTP 200 `{"status": "ok"}`.
16. `deploy.sh` exits 0 after successful deploy and restart.
17. `deploy.sh` exits non-zero with journalctl hint if service doesn't respond in 20s.
18. TRMNL device receives a valid BMP on its next poll after `deploy.sh` completes.

---

## Error Handling

- **Config file missing/unparseable on startup:** fall back to default mix, log WARNING
- **Unknown engine name in `POST /api/control/engine`:** HTTP 400, list valid names
- **`FantasyEngine` empty cache:** log ERROR, raise `RuntimeError`
- **`response.message.images` None or empty:** log error with slug, skip (background process)
- **Exception from `model.image.generate()`:** log slug + message, skip (background process)
- **Interrupted BMP write:** atomic temp-file rename prevents corrupt cache entries
- **`trmnl-ctl` connection failure:** clean message + exit 1, no traceback
- **`MixEngine` with empty engine list:** raise `ValueError` immediately at construction
- **Deploy `git pull` failure:** script aborts, service stays on previous version
- **Deploy timeout:** exit non-zero, print journalctl hint

---

## Out of Scope

- Authentication on admin endpoints (local network only — intentional)
- `MixEngine._index` persistence across restarts (resets to 0 — intentional)
- Concurrency protection on `EngineRouter.set_engine()` (single-user device — intentional)
- `trmnl-ctl` local filesystem writes (all persistence via server API — intentional)
- LLM-generated prompts (may revisit)
- `gpt-image-1` support in conduit (dall-e-3 is current)
- Concurrency in background process (cost control)
- Cache invalidation on preamble change (delete manually)
- BMP quality validation (eyeball manually)
- Retry-with-backoff on API failure (re-run script)
- Round-robin deduplication in `FantasyEngine` (pure random with replacement)
