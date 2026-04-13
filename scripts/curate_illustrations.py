#!/usr/bin/env python3
# scripts/curate_illustrations.py
"""
Interactive curation web app for TRMNL illustration images.

Reads /tmp/trmnl_illustrations/manifest.json, presents each image in a browser
UI, and saves accepted images as 800x480 1-bit BMPs to ~/.cache/trmnl/illustration/

Usage:
    uv run --with fastapi --with uvicorn --with pillow python scripts/curate_illustrations.py
"""
from __future__ import annotations

import json
import mimetypes
import webbrowser
from pathlib import Path
from threading import Timer
from typing import TYPE_CHECKING

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

if TYPE_CHECKING:
    pass

MANIFEST_PATH = Path("/tmp/trmnl_illustrations/manifest.json")
CACHE_DIR = Path.home() / ".cache" / "trmnl" / "illustration"
PORT = 8099

app = FastAPI()

# Module-level state — safe for single-worker uvicorn
_images: list[dict] = []
_current_index: int = 0
_included: list[dict] = []
_skipped: list[dict] = []


def _load_manifest() -> None:
    global _images
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"Manifest not found: {MANIFEST_PATH}\n"
            "Run scripts/fetch_illustration_images.py first."
        )
    _images = json.loads(MANIFEST_PATH.read_text())


def _convert_and_save(entry: dict) -> str:
    """Convert source image to 800x480 1-bit BMP. Returns output filename."""
    from PIL import Image, ImageOps

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    source = Path(entry["local_path"])
    slug = entry["slug"]
    stem = source.stem[:50]
    safe_stem = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in stem)
    filename = f"{slug}_{safe_stem}.bmp"
    output_path = CACHE_DIR / filename

    image = Image.open(source).convert("RGB")
    image = ImageOps.pad(image, (800, 480), color=(0, 0, 0))
    bmp = image.convert("1")
    bmp.save(output_path, format="BMP")

    return filename


_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>TRMNL Illustration Curator</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: monospace;
      background: #111;
      color: #ddd;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      gap: 0.75rem;
      padding: 1rem;
    }
    #info { font-size: 0.85rem; color: #888; }
    #artist { font-size: 1rem; color: #bbb; }
    #filename { font-size: 0.75rem; color: #555; max-width: 820px; word-break: break-all; }
    #image-wrap {
      background: #000;
      border: 1px solid #2a2a2a;
      width: 800px;
      height: 480px;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
    }
    #img { max-width: 800px; max-height: 480px; object-fit: contain; }
    .controls { display: flex; gap: 4rem; }
    button {
      font-family: monospace;
      font-size: 1.1rem;
      padding: 0.55rem 2.5rem;
      cursor: pointer;
      border: none;
      border-radius: 3px;
      letter-spacing: 0.05em;
    }
    button:disabled { opacity: 0.35; cursor: default; }
    .btn-skip    { background: #3a2a2a; color: #c88; }
    .btn-include { background: #1e3a1e; color: #8c8; }
    #summary { text-align: center; max-width: 700px; }
    #summary h2 { font-size: 1.4rem; margin-bottom: 1rem; color: #bbb; }
    #summary p  { margin: 0.4rem 0; color: #888; }
    #summary ul {
      margin-top: 1rem;
      list-style: none;
      font-size: 0.75rem;
      color: #555;
      text-align: left;
      max-height: 280px;
      overflow-y: auto;
    }
  </style>
</head>
<body>
  <div id="info">Loading...</div>
  <div id="artist"></div>
  <div id="filename"></div>
  <div id="image-wrap"><img id="img" src="" alt="illustration"></div>
  <div class="controls">
    <button class="btn-skip"    id="btn-skip"    onclick="act('skip')">Skip [&larr; / S]</button>
    <button class="btn-include" id="btn-include" onclick="act('include')">Include [&rarr; / Enter]</button>
  </div>
  <div id="summary" style="display:none"></div>

  <script>
    let busy = false;

    async function loadState() {
      const s = await fetch('/api/state').then(r => r.json());
      render(s);
    }

    function render(s) {
      if (s.done) {
        document.getElementById('image-wrap').style.display = 'none';
        document.querySelector('.controls').style.display  = 'none';
        document.getElementById('artist').style.display   = 'none';
        document.getElementById('filename').style.display = 'none';
        document.getElementById('info').textContent = 'Curation complete';
        const el = document.getElementById('summary');
        el.style.display = 'block';
        el.innerHTML =
          '<h2>Done</h2>' +
          '<p>' + s.included_count + ' included &nbsp; ' + s.skipped_count + ' skipped</p>' +
          '<p>Saved to ~/.cache/trmnl/illustration/</p>' +
          '<ul>' + s.included_files.map(f => '<li>' + f + '</li>').join('') + '</ul>';
        return;
      }
      document.getElementById('info').textContent =
        (s.index + 1) + ' / ' + s.total +
        '  \u2013  ' + s.included_count + ' included, ' + s.skipped_count + ' skipped';
      document.getElementById('artist').textContent   = s.current.artist;
      document.getElementById('filename').textContent = s.current.filename;
      document.getElementById('img').src = '/image/' + s.index + '?t=' + Date.now();
    }

    async function act(action) {
      if (busy) return;
      busy = true;
      document.getElementById('btn-skip').disabled    = true;
      document.getElementById('btn-include').disabled = true;
      try {
        await fetch('/api/action', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({action})
        });
        await loadState();
      } finally {
        busy = false;
        document.getElementById('btn-skip').disabled    = false;
        document.getElementById('btn-include').disabled = false;
      }
    }

    document.addEventListener('keydown', e => {
      if (e.key === 'ArrowRight' || e.key === 'Enter') act('include');
      if (e.key === 'ArrowLeft'  || e.key === 's')     act('skip');
    });

    loadState();
  </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(_HTML)


@app.get("/api/state")
async def get_state() -> dict:
    if _current_index >= len(_images):
        return {
            "done": True,
            "total": len(_images),
            "included_count": len(_included),
            "skipped_count": len(_skipped),
            "included_files": [e.get("output_filename", "") for e in _included],
        }
    entry = _images[_current_index]
    return {
        "done": False,
        "index": _current_index,
        "total": len(_images),
        "included_count": len(_included),
        "skipped_count": len(_skipped),
        "current": {
            "artist": entry["artist"],
            "filename": Path(entry["local_path"]).name,
            "slug": entry["slug"],
        },
    }


class ActionRequest(BaseModel):
    action: str


@app.post("/api/action")
async def post_action(req: ActionRequest) -> dict:
    global _current_index

    if _current_index >= len(_images):
        return {"status": "done"}

    if req.action not in ("include", "skip"):
        raise HTTPException(status_code=400, detail="action must be 'include' or 'skip'")

    entry = _images[_current_index]

    if req.action == "include":
        try:
            filename = _convert_and_save(entry)
            _included.append(dict(entry, output_filename=filename))
        except Exception as exc:
            _skipped.append(entry)
            _current_index += 1
            return {"status": "error", "message": str(exc)}
    else:
        _skipped.append(entry)

    _current_index += 1
    return {"status": "ok"}


@app.get("/image/{index}")
async def serve_image(index: int) -> Response:
    if index < 0 or index >= len(_images):
        raise HTTPException(status_code=404, detail="image not found")
    path = Path(_images[index]["local_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="file not on disk")
    content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return Response(content=path.read_bytes(), media_type=content_type)


if __name__ == "__main__":
    _load_manifest()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Loaded {len(_images)} images from manifest")
    print(f"Output directory: {CACHE_DIR}")
    print(f"Opening http://localhost:{PORT}")
    Timer(1.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
