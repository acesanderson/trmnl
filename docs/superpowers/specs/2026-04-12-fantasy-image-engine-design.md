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

```
src/trmnl/engines/fantasy/
    __init__.py
    engine.py               # FantasyEngine(ImageEngine) — picks random cached BMP
    prompts.py              # PROMPTS list of {slug, prompt} dicts
    background_process.py   # generates missing BMPs, idempotent

scripts/
    test_image_gen.py       # generates N style variants of one prompt for eyeballing
    deploy.sh               # push → pull caruana → uv sync → restart → health check

src/trmnl/app.py            # +GET /ping (health check endpoint)
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
    prompt_str=f"{STYLE_PREAMBLE} {prompt}",
    size="1792x1024",
    quality="hd",
    style="natural",
    response_format="b64_json",
)
```

**Post-processing:** `response.message.images[0].b64_json` → `base64.b64decode` → `Image.open(BytesIO(...))` → `image.resize((800, 480))` → `image.convert("1")` → `save(output_path)`. Done inline with Pillow — `image_to_bmp()` is not used here since it requires a file path input, not bytes.

---

## Style Preamble

Prepended to every prompt in the background script (single place to edit):

> "Albrecht Dürer woodcut engraving style, black and white only, fine crosshatching, stark contrast, dramatic chiaroscuro, no color, no gradients, 16th century German Renaissance printmaking aesthetic —"

Each `PROMPTS` entry contains only the scene description, not the style preamble.

---

## Prompts List (`prompts.py`)

```python
PROMPTS = [
    {"slug": "dragon_hoard", "prompt": "a dragon sleeping on its hoard of gold coins and jewels, curled up like a contented dog"},
    # ~20-30 total entries
]
```

**Slug** is a stable, filesystem-safe identifier. Cache filename: `fantasy_{slug}.bmp`.

Adding a new entry to `PROMPTS` and re-running the background script automatically generates the missing BMP — the list is the queue.

---

## Background Process (`background_process.py`)

Idempotent — safe to re-run at any time.

```
for each entry in PROMPTS:
    if fantasy_{slug}.bmp exists in cache → skip
    else → generate via DALL-E 3 → convert → save
```

Prints progress (Rich console, same pattern as poems background process). Exits cleanly when all prompts are covered. No concurrency — sequential to keep API costs predictable and avoid rate limits.

---

## FantasyEngine (`engine.py`)

Implements `ImageEngine` protocol (`async def next() -> Path`):

1. Glob `~/.cache/trmnl/fantasy/*.bmp`
2. If empty → raise `RuntimeError("No fantasy images cached. Run background_process.py first.")`
3. Return `random.choice(bmp_files)`

No API calls at runtime. No state.

---

## Testing Script (`scripts/test_image_gen.py`)

Generates 4-6 BMP variants of a single scene ("dragon sleeping on its hoard") using different prompt phrasings and/or style preamble variations (e.g. Dürer vs. Gustave Doré). All calls run concurrently via `asyncio.gather`. Output saved to `./test_output/test_{i}.bmp`. Filenames printed to stdout for easy `open`ing.

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
5. Poll `http://caruana:8070/ping` every 1s, up to 20s → exit 0 on success, exit 1 on timeout (with journalctl hint)

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
ExecStart=uv run trmnl
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable with: `sudo systemctl enable trmnl`

### `/ping` endpoint (`app.py`)

```python
@app.get("/ping")
async def ping():
    return {"status": "ok"}
```

---

## Error Handling

- **Empty cache at engine runtime:** raise `RuntimeError` with clear message pointing to background script
- **DALL-E 3 API failure in background script:** log the error and continue to next prompt (partial cache is valid)
- **Deploy timeout:** script exits non-zero and prints `journalctl -u trmnl -n 30` hint

---

## Out of Scope

- LLM-generated prompts (may revisit later)
- `gpt-image-1` support in conduit (dall-e-3 is the current supported model)
- Concurrency in background process (sequential is intentional — cost control)
- Approval/curation registry (delete unwanted BMPs manually and re-run)
