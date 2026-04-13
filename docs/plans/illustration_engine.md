# IllustrationEngine — Project Status

**Last updated:** 2026-04-12

## Goal

Add a curated illustration mode to the TRMNL e-ink display. Five artists
(Beardsley, Gorey, Kollwitz, Masereel, Escher) — ~20 images each — displayed
as random 800x480 1-bit BMPs, the same way the FantasyEngine works.

---

## Architecture

Three components, each independently usable:

```
scripts/fetch_illustration_images.py   # downloads images to /tmp/trmnl_illustrations/
scripts/curate_illustrations.py        # browser UI: include/skip → saves BMPs locally
src/trmnl/engines/illustration/        # engine reads ~/.cache/trmnl/illustration/*.bmp
```

The curation workflow is intentionally client/server split:
- Fetch + curate runs **locally** (MacBook)
- `scp ~/.cache/trmnl/illustration/*.bmp caruana:~/.cache/trmnl/illustration/` is a manual HITL step
- IllustrationEngine on Caruana just reads whatever BMPs are in the cache dir

---

## Status by component

### IllustrationEngine — DONE, deployed

- `src/trmnl/engines/illustration/__init__.py` (empty)
- `src/trmnl/engines/illustration/engine.py` — mirrors FantasyEngine exactly
- `src/trmnl/engines/registry.py` — `"illustration": IllustrationEngine` added
- `tests/test_illustration_engine.py` — 3 tests, all passing (23/23 suite)
- Deployed to Caruana via `bash scripts/deploy.sh` on 2026-04-12

To activate on Caruana, edit `~/.config/trmnl/config.yaml`:
```yaml
engine: illustration
```
Then `sudo systemctl restart trmnl`. (Don't do this until images are SCP'd over.)

### curate_illustrations.py — DONE, untested end-to-end

FastAPI + uvicorn server on port 8099. Run with:
```
uv run --with fastapi --with uvicorn --with pillow python scripts/curate_illustrations.py
```

- Reads `/tmp/trmnl_illustrations/manifest.json`
- Shows one image at a time; right arrow/Enter = include, left arrow/S = skip
- On include: PIL `ImageOps.pad(image, (800, 480)) → convert('1') → save(format='BMP')`
- Saves to `~/.cache/trmnl/illustration/<slug>_<stem>.bmp`
- Opens browser automatically; shows summary screen when done

Ready to use as soon as fetch succeeds.

### fetch_illustration_images.py — BLOCKED

Run with: `uv run python scripts/fetch_illustration_images.py`

#### What works
- Wikimedia Commons category API (`list=categorymembers`) correctly identifies artwork files
  - `Category:Illustrations by Aubrey Beardsley` — 159 files, correct artwork
  - `Category:Prints by Käthe Kollwitz` — 41 files, correct artwork
  - `Category:Works by Frans Masereel` — 8 files (sparse)
  - `Category:Works by M. C. Escher` — 13 files (sparse, most under copyright)
- Two-step pipeline: get file titles → batch `imageinfo` for URLs — works correctly

#### What's blocked
Wikimedia's `upload.wikimedia.org` CDN is aggressively rate-limiting bulk downloads:
- HTTP 429 (too many requests) escalated to HTTP 403 (soft IP block) after repeated attempts
- Even thumbnail URLs (`iiurlwidth=800`, served from the thumb cache) are blocked
- IP block is temporary; clears in ~30-60 minutes

#### Artist-specific notes
| Artist | Commons coverage | Notes |
|--------|-----------------|-------|
| Aubrey Beardsley | Excellent | 159 files in `Illustrations by Aubrey Beardsley` |
| Käthe Kollwitz | Good | 41 files in `Prints by Käthe Kollwitz` |
| Franz Masereel | Sparse | Only 8 files in `Works by Frans Masereel`; pre-1928 works should be PD |
| Edward Gorey | Very sparse | Died 2000 — PD expires ~2070; very little on Commons |
| MC Escher | Sparse | Died 1972, estate actively enforces; expires ~2042 in EU |

---

## Next steps

### Option A: Wait out the Wikimedia block (simplest)
Wait ~30-60 min, then re-run with conservative settings (5s delay between
downloads). Should work for Beardsley and Kollwitz. Masereel will be sparse.
Gorey and Escher will be thin regardless.

### Option B: Switch primary source to museum APIs (more robust)
- **Met Museum Open Access API** (`collectionapi.metmuseum.org`) — no auth, public domain confirmed, no CDN restrictions. Probed briefly; returns 39 results for various queries but not yet validated for these artists specifically.
- **Art Institute of Chicago API** (`api.artic.edu`) — IIIF protocol, free, no auth. Strong for American/European art.
- **Rijksmuseum API** — excellent for Masereel and Dutch artists.

### Option C: Substitute low-coverage artists
Replace Gorey and/or Escher with artists that have abundant PD artwork:
- **Gustave Doré** (d.1883) — same dark engraving aesthetic, thousands of images, fully PD
- **Ernst Haeckel** (d.1919) — highly detailed B&W scientific illustrations
- **Francisco Goya** (d.1828) — etchings and aquatints, abundant PD

### Option D: Fix Brave web-search fallback
The brave-web-search skill path is failing with "No such file or directory".
Need to verify `~/.claude/skills/brave-web-search` is properly installed and
`BRAVE_API_KEY` is set before the fallback can supplement Commons results.

---

## SCP command (HITL step, when images are ready)

```bash
scp ~/.cache/trmnl/illustration/*.bmp caruana:/home/bianders/.cache/trmnl/illustration/
```

Create the dir on Caruana first if needed:
```bash
ssh caruana 'mkdir -p ~/.cache/trmnl/illustration'
```
