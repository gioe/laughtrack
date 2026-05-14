"""Source comedian images from Wikidata (P18) and TMDb, upload to Bunny CDN.

Wikidata is tried first (free, CC-licensed). If no image is found, falls back to
TMDb person search (requires TMDB_API_KEY env var). Downloaded images are resized
to a max 500px width with Pillow and uploaded as PNG to Bunny CDN Storage.

All operations are synchronous and non-blocking — failures are logged but never
raised to callers.
"""

import io
import hashlib
import os
import re
import time
import urllib.parse
from typing import List, Optional

import requests
from PIL import Image

from laughtrack.foundation.infrastructure.logger.logger import Logger

# Wikidata SPARQL endpoint
_WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
_COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
_WIKIMEDIA_USER_AGENT = "LaughTrack/1.0 (comedy show aggregator; contact: gioematt@gmail.com)"

# TMDb API
_TMDB_API_URL = "https://api.themoviedb.org/3"
_TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# Bunny CDN
_CDN_HOST = "laughtrack.b-cdn.net"
_MAX_IMAGE_WIDTH = 500

# Only allow safe characters in SPARQL string literals
_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9 .'\-]+$")
_COMMONS_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

# Delay between per-comedian image sourcing requests to avoid rate-limiting
_IMAGE_SOURCE_DELAY_S = float(os.environ.get("IMAGE_SOURCE_DELAY_S", "5.0"))


def _escape_sparql_string(s: str) -> str:
    """Escape a string for safe inclusion in a SPARQL double-quoted literal.

    Handles backslashes, quotes, newlines, tabs, and carriage returns per the
    SPARQL 1.1 grammar (https://www.w3.org/TR/sparql11-query/#rString).
    """
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    s = s.replace("\t", "\\t")
    return s


def _wikimedia_upload_thumbnail_url(image_url: str) -> str:
    """Convert Commons Special:FilePath URLs to direct upload.wikimedia.org thumbnails."""
    parsed = urllib.parse.urlparse(image_url)
    if parsed.netloc.lower() != "commons.wikimedia.org" or not parsed.path.startswith("/wiki/Special:FilePath/"):
        return image_url

    raw_filename = parsed.path.removeprefix("/wiki/Special:FilePath/")
    filename = urllib.parse.unquote(raw_filename).replace(" ", "_")
    digest = hashlib.md5(filename.encode("utf-8")).hexdigest()
    quoted_filename = urllib.parse.quote(filename)
    return (
        f"https://upload.wikimedia.org/wikipedia/commons/thumb/{digest[0]}/{digest[:2]}/"
        f"{quoted_filename}/500px-{quoted_filename}"
    )


def _strip_url_query(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse(parsed._replace(query="", fragment=""))


def _commons_filename_matches_name(title: str, comedian_name: str) -> bool:
    if not title.startswith("File:"):
        return False

    filename = title.removeprefix("File:")
    if not filename.lower().endswith(_COMMONS_IMAGE_EXTENSIONS):
        return False

    normalized_filename = urllib.parse.unquote(filename).replace("_", " ").lower()
    normalized_name = comedian_name.lower()
    return normalized_filename.startswith(normalized_name)


def _get_commons_file_search_image_url(comedian_name: str) -> Optional[str]:
    """Search Commons for a direct thumbnail when Wikidata lacks a P18 image."""
    try:
        resp = requests.get(
            _COMMONS_API_URL,
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": comedian_name,
                "gsrnamespace": 6,
                "gsrlimit": 10,
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": _MAX_IMAGE_WIDTH,
            },
            headers={"User-Agent": _WIKIMEDIA_USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {}).values()
        for page in pages:
            title = page.get("title", "")
            if not _commons_filename_matches_name(title, comedian_name):
                continue
            image_info = page.get("imageinfo", [])
            if image_info:
                url = image_info[0].get("thumburl") or image_info[0].get("url")
                if url:
                    return _strip_url_query(url)
    except Exception as e:
        Logger.warn(f"image_sourcing: Commons image search failed for '{comedian_name}': {e}")
    return None


def _get_wikidata_image_url(comedian_name: str) -> Optional[str]:
    """Query Wikidata for a comedian's P18 (image) property via SPARQL.

    Returns the Wikimedia Commons image URL or None.
    """
    if not _SAFE_NAME_RE.match(comedian_name):
        Logger.warn(f"image_sourcing: skipping Wikidata lookup for '{comedian_name}' — name contains unsupported characters")
        return None

    escaped_name = _escape_sparql_string(comedian_name)
    query = f'''
    SELECT ?image WHERE {{
      ?person rdfs:label "{escaped_name}"@en ;
              wdt:P18 ?image .
    }}
    LIMIT 1
    '''

    try:
        resp = requests.get(
            _WIKIDATA_SPARQL_URL,
            params={"query": query, "format": "json"},
            headers={"User-Agent": _WIKIMEDIA_USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results", {}).get("bindings", [])
        if results:
            return _wikimedia_upload_thumbnail_url(results[0]["image"]["value"])
    except Exception as e:
        Logger.warn(f"image_sourcing: Wikidata lookup failed for '{comedian_name}': {e}")
    return _get_commons_file_search_image_url(comedian_name)


def _get_tmdb_image_url(comedian_name: str, api_key: str) -> Optional[str]:
    """Search TMDb for a person and return their profile image URL.

    Returns the full image URL at w500 resolution, or None.
    """
    try:
        resp = requests.get(
            f"{_TMDB_API_URL}/search/person",
            params={"api_key": api_key, "query": comedian_name},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if results and results[0].get("profile_path"):
            return f"{_TMDB_IMAGE_BASE}{results[0]['profile_path']}"
    except Exception as e:
        Logger.warn(f"image_sourcing: TMDb lookup failed for '{comedian_name}': {e}")
    return None


def _download_image(url: str) -> Optional[bytes]:
    """Download image bytes from a URL using requests (with default SSL verification)."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": _WIKIMEDIA_USER_AGENT},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        Logger.warn(f"image_sourcing: download failed for {url}: {e}")
        return None


def _resize_image(data: bytes, max_width: int = _MAX_IMAGE_WIDTH) -> bytes:
    """Resize image to max_width, preserving aspect ratio. Returns PNG bytes."""
    img = Image.open(io.BytesIO(data))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")

    if img.width > max_width:
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _upload_to_bunny_cdn(
    data: bytes,
    path: str,
    storage_password: str,
    storage_zone: str,
    region: str = "la",
) -> bool:
    """Upload image bytes to Bunny CDN Storage via synchronous PUT.

    Returns True on success (HTTP 201), False otherwise.
    """
    url = f"https://{region}.storage.bunnycdn.com/{storage_zone}/{path}"
    try:
        resp = requests.put(
            url,
            data=data,
            headers={
                "AccessKey": storage_password,
                "Content-Type": "image/png",
            },
            timeout=15,
        )
        if resp.status_code == 201:
            Logger.info(f"image_sourcing: uploaded {path} ({len(data)} bytes)")
            return True
        Logger.warn(f"image_sourcing: CDN upload failed for {path} — HTTP {resp.status_code}")
        return False
    except Exception as e:
        Logger.warn(f"image_sourcing: CDN upload error for {path}: {e}")
        return False


def fetch_comedian_image_png(comedian_name: str) -> Optional[bytes]:
    """Fetch and resize a headshot for a comedian without uploading.

    Tries Wikidata first, then TMDb (when ``TMDB_API_KEY`` is set). Returns
    the resized PNG bytes, or ``None`` if no image could be sourced.

    Splitting fetch from upload lets callers stage images locally for human
    review before publishing them to the CDN.
    """
    image_url = _get_wikidata_image_url(comedian_name)
    if not image_url:
        tmdb_key = os.environ.get("TMDB_API_KEY", "")
        if tmdb_key:
            image_url = _get_tmdb_image_url(comedian_name, tmdb_key)
    if not image_url:
        return None

    raw_data = _download_image(image_url)
    if not raw_data:
        return None

    try:
        return _resize_image(raw_data)
    except Exception as e:
        Logger.warn(f"image_sourcing: resize failed for '{comedian_name}': {e}")
        return None


def upload_comedian_image_png(comedian_name: str, png_data: bytes) -> bool:
    """Upload pre-fetched PNG bytes for a comedian to Bunny CDN.

    Returns True on success, False if credentials are missing or the upload
    fails. Resizes the input again so callers can pass arbitrary image bytes
    (jpeg/webp/png at any size) — output on the CDN is always normalized PNG
    at <= ``_MAX_IMAGE_WIDTH`` width.
    """
    storage_password = os.environ.get("BUNNYCDN_STORAGE_PASSWORD", "")
    storage_zone = os.environ.get("BUNNYCDN_STORAGE_ZONE", "")
    if not storage_password or not storage_zone:
        Logger.warn("image_sourcing: skipping upload — BUNNYCDN_STORAGE_PASSWORD or BUNNYCDN_STORAGE_ZONE not set")
        return False
    region = os.environ.get("BUNNYCDN_STORAGE_REGION", "la")

    try:
        png_data = _resize_image(png_data)
    except Exception as e:
        Logger.warn(f"image_sourcing: resize failed for '{comedian_name}': {e}")
        return False

    cdn_path = f"comedians/{urllib.parse.quote(comedian_name)}.png"
    return _upload_to_bunny_cdn(png_data, cdn_path, storage_password, storage_zone, region)


def source_comedian_image(comedian_name: str) -> bool:
    """Find, download, resize, and upload a headshot for a comedian.

    Tries Wikidata first, then TMDb. Uploads to Bunny CDN as
    ``comedians/{name}.png``. Returns True on success, False otherwise.
    """
    png_data = fetch_comedian_image_png(comedian_name)
    if png_data is None:
        return False
    return upload_comedian_image_png(comedian_name, png_data)


def source_images_for_comedians(
    comedian_names: List[str],
) -> List[str]:
    """Source images for a list of comedian names.

    Returns the list of names for which images were successfully uploaded.
    This function never raises — all errors are caught and logged.
    """
    if not comedian_names:
        return []

    # Early exit if CDN credentials are not configured
    if not os.environ.get("BUNNYCDN_STORAGE_PASSWORD") or not os.environ.get("BUNNYCDN_STORAGE_ZONE"):
        Logger.info("image_sourcing: skipping — BUNNYCDN_STORAGE_PASSWORD or BUNNYCDN_STORAGE_ZONE not set")
        return []

    sourced: List[str] = []
    for i, name in enumerate(comedian_names):
        try:
            if source_comedian_image(name):
                sourced.append(name)
        except Exception as e:
            Logger.warn(f"image_sourcing: unexpected error for '{name}': {e}")
        # Rate-limit between requests to avoid hitting API limits
        if i < len(comedian_names) - 1:
            time.sleep(_IMAGE_SOURCE_DELAY_S)

    if sourced:
        Logger.info(f"image_sourcing: found images for {len(sourced)}/{len(comedian_names)} new comedians")
    return sourced
