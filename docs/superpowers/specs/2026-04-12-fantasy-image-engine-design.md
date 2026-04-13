# Fantasy Image Engine — Design Spec

**Date:** 2026-04-12
**Status:** Approved

---

## Overview

A new `FantasyEngine` that serves AI-generated fantasy illustrations to the TRMNL e-ink display. Images are generated once via DALL-E 3, converted to 800x480 1-bit BMP, and cached permanently. At runtime the engine picks randomly from the cache — zero API calls after initial generation.

A testing script (`scripts/test_image_gen.py`) validates prompt/style choices against actual hardware before committing to a full prompt list.

A deploy script (`scripts/deploy.sh`) and systemd service enable a fast inner loop: edit locally → push → auto-deploy to caruana → service restarts → visible on physical device.

---

## File Layout

All `scripts/` paths are at the project root (same level as `src/`, `pyproject.toml`).

```
src/trmnl/engines/fantasy/
    __init__.py             # empty — no public API for this module
    engine.py               # FantasyEngine(ImageEngine) — picks random cached BMP
    prompts.py              # STYLE_PREAMBLE constant + PROMPTS list
    background_process.py   # generates missing BMPs, idempotent

scripts/
    test_image_gen.py       # generates style variants of one prompt for eyeballing
    deploy.sh               # push → pull caruana → uv sync → restart → health check

src/trmnl/app.py            # +GET /ping (health check endpoint)
src/trmnl/config.py         # default_engine() updated to return FantasyEngine()
```

Cache dir: `~/.cache/trmnl/fantasy/` (XDG, same pattern as poems).

---

## Image Generation

**Model:** `dall-e-3` via `conduit.core.model.model_async.ModelAsync`

**Parameters:**
- `size="1792x1024"` — DALL-E 3's only landscape option (1.75:1, resizes cleanly to 800x480)
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

**Post-processing:** `response.message.images[0].b64_json` → `base64.b64decode` → `Image.open(BytesIO(...))` → `image.resize((800, 480))` → `image.convert("1")` → `save(output_path)`. Done inline with Pillow — `image_to_bmp()` is not used here since it requires a file path input, not bytes.

**Write atomically:** write to `fantasy_{slug}.bmp.tmp`, then `Path.rename()` to `fantasy_{slug}.bmp` on success. This prevents a corrupt BMP being left at the final path if the process is interrupted mid-write.

---

## Style Preamble

Defined as `STYLE_PREAMBLE` in `prompts.py` (alongside `PROMPTS`). Prepended to every prompt at generation time — not stored in the `PROMPTS` entries.

```python
STYLE_PREAMBLE = (
    "Albrecht Dürer woodcut engraving style, black and white only, "
    "fine crosshatching, stark contrast, dramatic chiaroscuro, no color, "
    "no gradients, 16th century German Renaissance printmaking aesthetic —"
)
```

If `STYLE_PREAMBLE` is changed, existing cached BMPs are not invalidated automatically. Delete the cache dir manually and re-run the background process to regenerate with the new preamble.

---

## Prompts List (`prompts.py`)

```python
PROMPTS = [
    {"slug": "dragon_hoard", "prompt": "a dragon sleeping on its hoard of gold coins and jewels, curled up like a contented dog"},
    # 20-30 total entries
]
```

**`prompt` field:** scene description only — plain English, no style guidance. The full generation prompt is always `f"{STYLE_PREAMBLE} {entry['prompt']}"`, assembled in `background_process.py`.

**`slug`:** stable, filesystem-safe identifier (lowercase, underscores only). Cache filename: `fantasy_{slug}.bmp`. Never change a slug after its BMP has been generated — it will appear as a new uncached entry on the next run.

Adding a new entry and re-running the background script generates the missing BMP — the list is the queue.

---

## Background Process (`background_process.py`)

Idempotent — safe to re-run at any time. Run locally (not on caruana) since `OPENAI_API_KEY` is in the local environment.

```
for each entry in PROMPTS:
    if fantasy_{slug}.bmp exists in cache → log skip, continue
    else:
        call ModelAsync("dall-e-3").image.generate(...)
        if response.message.images is None or empty → log error, continue
        write to fantasy_{slug}.bmp.tmp
        rename to fantasy_{slug}.bmp
        log: filename + file size in bytes

print summary: N generated, M skipped, K failed
```

**On any exception from `model.image.generate()`:** log the slug and exception message, continue to next entry. Partial cache is valid — re-run to pick up failures.

**No concurrency** — sequential to keep API costs predictable and avoid rate limits.

**No retry logic** — log and continue. Re-run the script to recover failed slugs.

Rich console output (`console.print`), same pattern as poems background process.

---

## FantasyEngine (`engine.py`)

Implements `ImageEngine` protocol (`async def next() -> Path`).

At module load: `FANTASY_DIR.mkdir(parents=True, exist_ok=True)` — creates the cache dir if absent.

At startup (when engine is instantiated): log at INFO the count of cached BMPs in `FANTASY_DIR`.

**`next()` implementation:**
1. Glob `FANTASY_DIR / "*.bmp"`
2. If empty → log at ERROR, raise `RuntimeError("No fantasy images cached. Run background_process.py first.")`
3. Pick via `random.choice(bmp_files)` — pure random with replacement (same image may appear consecutively)
4. Log at INFO: selected filename
5. Return the `Path`

No API calls at runtime. No state persisted between calls.

---

## Testing Script (`scripts/test_image_gen.py`)

Generates 4-6 BMP variants of a single scene ("dragon sleeping on its hoard") using different prompt phrasings and/or style preamble variations (e.g. Dürer vs. Gustave Doré). All calls run concurrently via `asyncio.gather`. Output dir: `Path(__file__).parent.parent / "test_output"` (anchored to project root regardless of CWD). Saves as `test_0.bmp`, `test_1.bmp`, etc. Prints absolute paths to stdout for easy `open`ing.

Goal: eyeball actual BMP output on screen (or push to device) before committing to the full prompt list.

---

## Deploy & Daemonization

### `scripts/deploy.sh`

Modeled on `$BC/siphon/scripts/deploy.sh` and `$BC/headwater/scripts/deploy.sh`.

Steps:
1. `git push` local branch to GitHub
2. SSH caruana → `git -C /home/bianders/Brian_Code/trmnl-project pull --ff-only` (with `GITHUB_PERSONAL_TOKEN`)
3. SSH caruana → `cd /home/bianders/Brian_Code/trmnl-project && uv sync`
4. SSH caruana → `sudo systemctl restart trmnl`
5. Poll `http://caruana:8070/ping` every 1s, up to 20s → exit 0 on success, exit 1 on timeout (with `journalctl -u trmnl -n 30` hint)

If `git pull --ff-only` fails (e.g. caruana has diverged), `set -euo pipefail` aborts the script. The service continues running on the previous version. Resolve the divergence manually before re-deploying.

Usage:
```bash
bash scripts/deploy.sh
```

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

`/home/bianders/.config/trmnl/env` holds secrets not needed by the live service at runtime (the service itself makes no API calls — only the background process does). The file should exist and be valid even if empty, since `EnvironmentFile` is specified. If future engines require API keys at runtime, add them here.

Enable with: `sudo systemctl enable trmnl && sudo systemctl daemon-reload`

**Note:** `/home/bianders/.local/bin/uv` is the standard `uv` install path. Confirm on caruana with `which uv` before writing the unit file.

### `/ping` endpoint (`app.py`)

```python
@app.get("/ping")
async def ping():
    return {"status": "ok"}
```

---

## Observability

### Engine (systemd service — visible via `journalctl -u trmnl -f`)

- **Startup:** `INFO — FantasyEngine initialized with {n} cached images`
- **Each `next()` call:** `INFO — FantasyEngine serving: {filename}`
- **Empty cache:** `ERROR — FantasyEngine: no images in cache` (then raises)

### Background Process (local, stdout)

- Per skip: `[blue]Skipping {slug} (already cached)[/blue]`
- Per generation: `[green]Generated {slug}[/green] → {path} ({size} bytes)`
- Per failure: `[red]Failed {slug}[/red]: {exception}`
- Final line: `Done: {n_generated} generated, {m_skipped} skipped, {k_failed} failed`

---

## Acceptance Criteria

All of the following must be true before the implementation is considered complete:

1. Running `background_process.py` with `PROMPTS = [{"slug": "dragon_hoard", ...}]` produces `~/.cache/trmnl/fantasy/fantasy_dragon_hoard.bmp`.
2. Re-running `background_process.py` does not regenerate `fantasy_dragon_hoard.bmp` (file mtime is unchanged).
3. `fantasy_dragon_hoard.bmp` is exactly 800×480 pixels, 1-bit depth, and under 90 KB.
4. `FantasyEngine.next()` returns a `Path` ending in `.bmp` when the cache dir is non-empty.
5. `FantasyEngine.next()` raises `RuntimeError` containing the word "background_process" when the cache dir is empty.
6. `GET /ping` returns HTTP 200 with body `{"status": "ok"}`.
7. `deploy.sh` exits 0 after a successful deploy and service restart.
8. `deploy.sh` exits non-zero and prints a `journalctl` hint if the service does not respond within 20s.
9. The TRMNL device receives a valid BMP on its next poll after `deploy.sh` completes.

---

## Error Handling

- **Empty cache at engine runtime:** log ERROR, raise `RuntimeError` with message pointing to background script
- **`response.message.images` is `None` or empty:** log error with slug, skip to next prompt (not an exception — a malformed-but-successful API response)
- **Exception from `model.image.generate()`:** log slug + exception message, skip to next prompt
- **Interrupted write:** atomic write (temp file → rename) prevents corrupt BMPs from being cached
- **Deploy `git pull` failure (non-fast-forward):** script aborts, service stays on previous version
- **Deploy timeout:** script exits non-zero, prints `journalctl -u trmnl -n 30` hint

---

## Out of Scope

- LLM-generated prompts (may revisit later)
- `gpt-image-1` support in conduit (dall-e-3 is the current supported model)
- Concurrency in background process (sequential is intentional — cost control)
- Approval/curation registry (delete unwanted BMPs manually and re-run)
- Cache invalidation on preamble change (delete cache dir manually)
- BMP quality validation (no automated check for all-black or corrupt images — eyeball manually)
- Retry-with-backoff on API failure (re-run the script to recover)
- Round-robin or recently-shown deduplication in the engine (pure random with replacement)
