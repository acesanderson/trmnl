#!/usr/bin/env python3
# scripts/fetch_illustration_images.py
"""
Fetch ~20 illustration images per artist using Wikimedia Commons category API
and Brave web search as a fallback for artists with limited Commons coverage.

Saves images to /tmp/trmnl_illustrations/<artist_slug>/
Writes manifest to /tmp/trmnl_illustrations/manifest.json

Usage:
    uv run python scripts/fetch_illustration_images.py

Requires:
    - BRAVE_API_KEY env var (only needed for Gorey/Escher fallback)
    - ~/.claude/skills/brave-web-search installed
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SEARCH_SKILL = Path.home() / ".claude" / "skills" / "brave-web-search"
OUTPUT_DIR = Path("/tmp/trmnl_illustrations")
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
IMAGES_PER_ARTIST = 20
REQUEST_DELAY = 0.4
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "trmnl-illustration-curator/1.0 (github.com/acesanderson/trmnl; brian@example.com) Python/3"

# Artists with known Commons categories for their actual artwork.
# Gorey (d.2000) and Escher (d.1972, estate active) have minimal PD content on
# Commons — they rely on brave-web-search for supplemental images.
ARTISTS: list[dict] = [
    {
        "name": "Aubrey Beardsley",
        "slug": "beardsley",
        # Beardsley died 1898 — extensively catalogued on Commons
        "commons_categories": [
            "Illustrations by Aubrey Beardsley",
            "Works by Aubrey Beardsley",
        ],
        "brave_queries": [],
    },
    {
        "name": "Edward Gorey",
        "slug": "gorey",
        # Died 2000 — most work under copyright; Commons has very little
        "commons_categories": [],
        "brave_queries": [
            "Edward Gorey illustration drawing site:commons.wikimedia.org",
            "Edward Gorey crosshatching black white art public domain",
            "Edward Gorey illustration filetype:jpg",
        ],
    },
    {
        "name": "Kathe Kollwitz",
        "slug": "kollwitz",
        # Died 1945 — PD in most countries since 2015
        "commons_categories": [
            "Works by Käthe Kollwitz",
            "Prints by Käthe Kollwitz",
        ],
        "brave_queries": [],
    },
    {
        "name": "Franz Masereel",
        "slug": "masereel",
        # Died 1972 — pre-1928 woodcut novels are PD in the US
        "commons_categories": [
            "Works by Frans Masereel",
            "Woodcuts by Frans Masereel",
        ],
        "brave_queries": [],
    },
    {
        "name": "MC Escher",
        "slug": "escher",
        # Died 1972 — estate actively enforces; sparse on Commons
        "commons_categories": [
            "Works by M. C. Escher",
        ],
        "brave_queries": [
            "MC Escher lithograph woodcut site:commons.wikimedia.org",
            "Escher mathematical art impossible figure public domain",
        ],
    },
]

IMAGE_MIMES = {"image/jpeg", "image/png", "image/gif"}
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif")


# ---------------------------------------------------------------------------
# Wikimedia Commons helpers
# ---------------------------------------------------------------------------

def _commons_get(params: dict) -> dict:
    """Single Commons API call, returns parsed JSON or {}."""
    url = COMMONS_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.debug(f"Commons API error: {e}")
        return {}


def fetch_category_file_titles(category: str, limit: int = 100) -> list[str]:
    """Return file titles (e.g. 'File:Foo.jpg') from a Commons category."""
    titles: list[str] = []
    params: dict = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmtype": "file",
        "cmprop": "title",
        "cmlimit": str(min(limit, 500)),
        "format": "json",
    }
    while len(titles) < limit:
        data = _commons_get(params)
        members = data.get("query", {}).get("categorymembers", [])
        for m in members:
            t = m.get("title", "")
            if t:
                titles.append(t)
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont or len(titles) >= limit:
            break
        params["cmcontinue"] = cont
        time.sleep(0.2)
    return titles[:limit]


def titles_to_image_urls(titles: list[str]) -> list[str]:
    """Batch-resolve file titles to thumbnail URLs via imageinfo.

    Uses iiurlwidth=1200 to request a cached thumbnail — Wikimedia rate-limits
    raw full-resolution downloads (HTTP 429) but serves cached thumbnail sizes freely.
    """
    if not titles:
        return []
    urls: list[str] = []
    # API allows up to 50 titles per request
    for i in range(0, len(titles), 50):
        batch = titles[i : i + 50]
        params = {
            "action": "query",
            "titles": "|".join(batch),
            "prop": "imageinfo",
            "iiprop": "url|mime|thumburl",
            "iiurlwidth": "800",  # exact display width; smaller = faster; cached size
            "format": "json",
        }
        data = _commons_get(params)
        for page in data.get("query", {}).get("pages", {}).values():
            info = page.get("imageinfo", [{}])
            if info:
                mime = info[0].get("mime", "")
                # Prefer thumburl (rate-limit-safe), fall back to url
                url = info[0].get("thumburl") or info[0].get("url", "")
                if url and mime in IMAGE_MIMES:
                    urls.append(url)
        time.sleep(0.3)
    return urls


def fetch_category_image_urls(category: str, limit: int = 60) -> list[str]:
    """Full pipeline: category → file titles → image URLs."""
    logger.info(f"  Category '{category}'...")
    titles = fetch_category_file_titles(category, limit=limit)
    if not titles:
        logger.info(f"    (empty or not found)")
        return []
    logger.info(f"    {len(titles)} file titles, resolving URLs...")
    urls = titles_to_image_urls(titles)
    logger.info(f"    {len(urls)} image URLs")
    return urls


def wikimedia_file_page_to_image_url(file_page_url: str) -> str | None:
    """Resolve a Commons file page URL to a direct image URL."""
    if "/wiki/File:" not in file_page_url:
        return None
    raw = file_page_url.split("/wiki/File:")[-1].split("?")[0]
    title = "File:" + urllib.parse.unquote(raw)
    data = _commons_get({
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "format": "json",
    })
    for page in data.get("query", {}).get("pages", {}).values():
        info = page.get("imageinfo", [{}])
        if info:
            mime = info[0].get("mime", "")
            url = info[0].get("url", "")
            if url and mime in IMAGE_MIMES:
                return url
    return None


# ---------------------------------------------------------------------------
# Brave web-search fallback
# ---------------------------------------------------------------------------

def search_brave(query: str) -> list[str]:
    """Run brave-web-search, return result URLs."""
    cmd = [
        "uv", "run", "--directory", str(SEARCH_SKILL),
        "python", "conduit.py", "search", query,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if result.returncode != 0:
            logger.warning(f"Brave search failed: {result.stderr[:150]}")
            return []
        data = json.loads(result.stdout)
        items: list[dict] = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (
                data.get("results")
                or data.get("web", {}).get("results", [])
                or []
            )
        return [
            item.get("url") or item.get("link") or ""
            for item in items
            if isinstance(item, dict)
        ]
    except Exception as e:
        logger.warning(f"Brave search error: {e}")
        return []


def is_direct_image_url(url: str) -> bool:
    path = urllib.parse.urlparse(url).path.lower().split("?")[0]
    return path.endswith(IMAGE_EXTENSIONS)


# ---------------------------------------------------------------------------
# Downloading
# ---------------------------------------------------------------------------

def slugify(url: str, index: int) -> str:
    path = urllib.parse.urlparse(url).path
    basename = urllib.parse.unquote(path.split("/")[-1])
    safe = "".join(c if c.isalnum() or c in (".", "_", "-") else "_" for c in basename)
    return safe if safe and safe != "." else f"image_{index:03d}.jpg"


def download_image(url: str, dest: Path) -> bool:
    """Download with retry + exponential backoff on HTTP 429."""
    import urllib.error
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
            if len(content) < 500:
                logger.debug(f"Skipping tiny response ({len(content)}B)")
                return False
            dest.write_bytes(content)
            return True
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 8 * (2 ** attempt)  # 8s, 16s, 32s, 64s
                logger.warning(f"429 rate limited (attempt {attempt+1}), waiting {wait}s...")
                time.sleep(wait)
            else:
                logger.warning(f"HTTP {e.code}: {url[:80]}")
                return False
        except Exception as e:
            logger.warning(f"Download failed: {type(e).__name__}: {e}")
            return False
    logger.warning(f"Gave up after 4 attempts: {url[:80]}")
    return False


# ---------------------------------------------------------------------------
# Per-artist orchestration
# ---------------------------------------------------------------------------

def collect_candidate_urls(artist: dict) -> list[str]:
    seen: dict[str, None] = {}

    # Primary: Commons category membership
    for cat in artist.get("commons_categories", []):
        for u in fetch_category_image_urls(cat, limit=60):
            seen[u] = None
        if len(seen) >= IMAGES_PER_ARTIST * 3:
            break

    # Fallback: brave-web-search (used for Gorey, Escher)
    for query in artist.get("brave_queries", []):
        if len(seen) >= IMAGES_PER_ARTIST * 3:
            break
        for page_url in search_brave(query):
            if "commons.wikimedia.org/wiki/File:" in page_url:
                img_url = wikimedia_file_page_to_image_url(page_url)
                if img_url:
                    seen[img_url] = None
            elif is_direct_image_url(page_url):
                seen[page_url] = None
        time.sleep(REQUEST_DELAY)

    logger.info(f"  {len(seen)} total candidate URLs")
    return list(seen.keys())


def fetch_artist(artist: dict) -> list[dict]:
    slug = artist["slug"]
    name = artist["name"]
    dest_dir = OUTPUT_DIR / slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"=== {name} ===")
    candidates = collect_candidate_urls(artist)

    entries: list[dict] = []
    count = 0

    for i, url in enumerate(candidates):
        if count >= IMAGES_PER_ARTIST:
            break
        filename = slugify(url, i)
        dest = dest_dir / filename

        if dest.exists():
            entries.append({"artist": name, "slug": slug, "local_path": str(dest), "source_url": url})
            count += 1
            continue

        logger.info(f"  [{count + 1}/{IMAGES_PER_ARTIST}] {filename}")
        if download_image(url, dest):
            entries.append({"artist": name, "slug": slug, "local_path": str(dest), "source_url": url})
            count += 1
        time.sleep(2.0)

    logger.info(f"  Done: {count}/{IMAGES_PER_ARTIST} images\n")
    return entries


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    for artist in ARTISTS:
        entries = fetch_artist(artist)
        manifest.extend(entries)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    logger.info(f"Manifest: {MANIFEST_PATH} ({len(manifest)} entries)")


if __name__ == "__main__":
    main()
