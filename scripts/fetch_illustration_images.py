#!/usr/bin/env python3
# scripts/fetch_illustration_images.py
"""
Fetch ~20 illustration images per artist using Brave web search + Wikimedia Commons API.

Saves images to /tmp/trmnl_illustrations/<artist_slug>/
Writes manifest to /tmp/trmnl_illustrations/manifest.json

Usage:
    uv run python scripts/fetch_illustration_images.py

Requires:
    - BRAVE_API_KEY env var
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
REQUEST_DELAY = 0.8

ARTISTS: list[dict] = [
    {
        "name": "Aubrey Beardsley",
        "slug": "beardsley",
        "queries": [
            "Aubrey Beardsley illustration site:commons.wikimedia.org",
            "Aubrey Beardsley art nouveau ink drawing public domain wikimedia",
        ],
        "commons_search": "Aubrey Beardsley",
    },
    {
        "name": "Edward Gorey",
        "slug": "gorey",
        "queries": [
            "Edward Gorey illustration site:commons.wikimedia.org",
            "Edward Gorey crosshatching black white drawing public domain",
        ],
        "commons_search": "Edward Gorey",
    },
    {
        "name": "Kathe Kollwitz",
        "slug": "kollwitz",
        "queries": [
            "Kathe Kollwitz etching site:commons.wikimedia.org",
            "Kollwitz printmaking charcoal expressionist public domain wikimedia",
        ],
        "commons_search": "Käthe Kollwitz",
    },
    {
        "name": "Franz Masereel",
        "slug": "masereel",
        "queries": [
            "Franz Masereel woodcut site:commons.wikimedia.org",
            "Franz Masereel black white woodcut public domain wikimedia",
        ],
        "commons_search": "Franz Masereel",
    },
    {
        "name": "MC Escher",
        "slug": "escher",
        "queries": [
            "MC Escher lithograph site:commons.wikimedia.org",
            "Escher mathematical impossible figure public domain wikimedia",
        ],
        "commons_search": "M.C. Escher",
    },
]

IMAGE_MIMES = {"image/jpeg", "image/png", "image/gif"}
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif")


def search_brave(query: str) -> list[str]:
    """Run brave-web-search and return list of result URLs."""
    cmd = [
        "uv", "run", "--directory", str(SEARCH_SKILL),
        "python", "conduit.py", "search", query,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if result.returncode != 0:
            logger.warning(f"Search failed for '{query}': {result.stderr[:200]}")
            return []
        data = json.loads(result.stdout)
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (
                data.get("results")
                or data.get("web", {}).get("results", [])
                or []
            )
        else:
            return []
        urls = []
        for item in items:
            if isinstance(item, dict):
                url = item.get("url") or item.get("link") or ""
                if url:
                    urls.append(url)
        return urls
    except json.JSONDecodeError:
        logger.warning(f"Could not parse search output for '{query}'")
        return []
    except Exception as e:
        logger.warning(f"Search error for '{query}': {e}")
        return []


def search_wikimedia_commons(search_term: str, limit: int = 25) -> list[str]:
    """Search Wikimedia Commons for images; return direct image URLs."""
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": search_term,
        "gsrnamespace": "6",
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "format": "json",
        "gsrlimit": str(limit),
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "trmnl-curator/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        pages = data.get("query", {}).get("pages", {})
        urls = []
        for page in pages.values():
            info = page.get("imageinfo", [{}])
            if info:
                mime = info[0].get("mime", "")
                img_url = info[0].get("url", "")
                if img_url and mime in IMAGE_MIMES:
                    urls.append(img_url)
        return urls
    except Exception as e:
        logger.warning(f"Wikimedia Commons API error for '{search_term}': {e}")
        return []


def wikimedia_file_page_to_image_url(file_page_url: str) -> str | None:
    """Resolve a Wikimedia Commons file page URL to a direct image URL."""
    if "/wiki/File:" not in file_page_url:
        return None
    raw = file_page_url.split("/wiki/File:")[-1].split("?")[0]
    file_title = "File:" + urllib.parse.unquote(raw)
    params = {
        "action": "query",
        "titles": file_title,
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "format": "json",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "trmnl-curator/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            info = page.get("imageinfo", [{}])
            if info:
                mime = info[0].get("mime", "")
                img_url = info[0].get("url", "")
                if img_url and mime in IMAGE_MIMES:
                    return img_url
    except Exception as e:
        logger.debug(f"Could not resolve {file_page_url}: {e}")
    return None


def is_direct_image_url(url: str) -> bool:
    path = urllib.parse.urlparse(url).path.lower().split("?")[0]
    return path.endswith(IMAGE_EXTENSIONS)


def slugify(url: str, index: int) -> str:
    path = urllib.parse.urlparse(url).path
    basename = urllib.parse.unquote(path.split("/")[-1])
    safe = "".join(c if c.isalnum() or c in (".", "_", "-") else "_" for c in basename)
    return safe if safe and safe != "." else f"image_{index:03d}.jpg"


def download_image(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; trmnl-curator/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            content = resp.read()
        if len(content) < 500:
            return False
        dest.write_bytes(content)
        return True
    except Exception as e:
        logger.debug(f"Download failed for {url}: {e}")
        return False


def collect_candidate_urls(artist: dict) -> list[str]:
    """Gather candidate image URLs for an artist from all sources."""
    urls: dict[str, None] = {}  # ordered set

    # Primary: Wikimedia Commons API
    for u in search_wikimedia_commons(artist["commons_search"], limit=30):
        urls[u] = None
    logger.info(f"  Wikimedia Commons API: {len(urls)} URLs")

    if len(urls) < IMAGES_PER_ARTIST:
        # Supplement: brave-web-search results
        for query in artist["queries"]:
            for page_url in search_brave(query):
                if "commons.wikimedia.org/wiki/File:" in page_url:
                    img_url = wikimedia_file_page_to_image_url(page_url)
                    if img_url:
                        urls[img_url] = None
                elif is_direct_image_url(page_url):
                    urls[page_url] = None
            time.sleep(REQUEST_DELAY)
        logger.info(f"  After web search: {len(urls)} candidate URLs")

    return list(urls.keys())


def fetch_artist(artist: dict) -> list[dict]:
    """Download images for one artist. Returns manifest entries."""
    slug = artist["slug"]
    name = artist["name"]
    dest_dir = OUTPUT_DIR / slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Fetching images for {name}...")
    candidates = collect_candidate_urls(artist)

    entries: list[dict] = []
    count = 0

    for i, url in enumerate(candidates):
        if count >= IMAGES_PER_ARTIST:
            break
        filename = slugify(url, i)
        dest = dest_dir / filename

        if dest.exists():
            logger.info(f"  Already exists: {filename}")
            entries.append(
                {"artist": name, "slug": slug, "local_path": str(dest), "source_url": url}
            )
            count += 1
            continue

        logger.info(f"  [{count + 1}/{IMAGES_PER_ARTIST}] {filename}")
        if download_image(url, dest):
            entries.append(
                {"artist": name, "slug": slug, "local_path": str(dest), "source_url": url}
            )
            count += 1
        time.sleep(0.3)

    logger.info(f"  Done: {count} images for {name}")
    return entries


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    for artist in ARTISTS:
        entries = fetch_artist(artist)
        manifest.extend(entries)

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    logger.info(f"Manifest saved to {MANIFEST_PATH} ({len(manifest)} total entries)")


if __name__ == "__main__":
    main()
