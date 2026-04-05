"""Source comedian images from Wikidata (P18) and TMDb, upload to Bunny CDN.

Wikidata is tried first (free, CC-licensed). If no image is found, falls back to
TMDb person search (requires TMDB_API_KEY env var). Downloaded images are resized
to a max 500px width with Pillow and uploaded as PNG to Bunny CDN Storage.

All operations are synchronous and non-blocking — failures are logged but never
raised to callers.
"""

import io
import os
import ssl
import urllib.parse
import urllib.request
from typing import List, Optional, Tuple

import requests
from PIL import Image

from laughtrack.foundation.infrastructure.logger.logger import Logger

# Wikidata SPARQL endpoint
_WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

# TMDb API
_TMDB_API_URL = "https://api.themoviedb.org/3"
_TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# Bunny CDN
_CDN_HOST = "laughtrack.b-cdn.net"
_MAX_IMAGE_WIDTH = 500

# Shared SSL context for image downloads (some CDNs have cert issues)
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _get_wikidata_image_url(comedian_name: str) -> Optional[str]:
    """Query Wikidata for a comedian's P18 (image) property via SPARQL.

    Returns the Wikimedia Commons image URL or None.
    """
    query = """
    SELECT ?image WHERE {
      ?person rdfs:label "%s"@en ;
              wdt:P18 ?image .
    }
    LIMIT 1
    """ % comedian_name.replace('"', '\\"')

    try:
        resp = requests.get(
            _WIKIDATA_SPARQL_URL,
            params={"query": query, "format": "json"},
            headers={"User-Agent": "LaughTrack/1.0 (comedy show aggregator)"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("results", {}).get("bindings", [])
        if results:
            return results[0]["image"]["value"]
    except Exception as e:
        Logger.warn(f"image_sourcing: Wikidata lookup failed for '{comedian_name}': {e}")
    return None


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
    """Download image bytes from a URL."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "LaughTrack/1.0 (comedy show aggregator)",
        })
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=15) as r:
            return r.read()
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


def source_comedian_image(comedian_name: str) -> bool:
    """Attempt to find, download, resize, and upload an image for a comedian.

    Tries Wikidata first, then TMDb. Uploads to Bunny CDN as
    ``comedians/{name}.png``.

    Returns True if an image was successfully uploaded, False otherwise.
    """
    # Bunny CDN config — required for upload
    storage_password = os.environ.get("BUNNYCDN_STORAGE_PASSWORD", "")
    storage_zone = os.environ.get("BUNNYCDN_STORAGE_ZONE", "")
    if not storage_password or not storage_zone:
        return False

    region = os.environ.get("BUNNYCDN_STORAGE_REGION", "la")

    # Try Wikidata first
    image_url = _get_wikidata_image_url(comedian_name)

    # Fall back to TMDb
    if not image_url:
        tmdb_key = os.environ.get("TMDB_API_KEY", "")
        if tmdb_key:
            image_url = _get_tmdb_image_url(comedian_name, tmdb_key)

    if not image_url:
        return False

    # Download
    raw_data = _download_image(image_url)
    if not raw_data:
        return False

    # Resize
    try:
        png_data = _resize_image(raw_data)
    except Exception as e:
        Logger.warn(f"image_sourcing: resize failed for '{comedian_name}': {e}")
        return False

    # Upload
    cdn_path = f"comedians/{urllib.parse.quote(comedian_name)}.png"
    return _upload_to_bunny_cdn(png_data, cdn_path, storage_password, storage_zone, region)


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
    for name in comedian_names:
        try:
            if source_comedian_image(name):
                sourced.append(name)
        except Exception as e:
            Logger.warn(f"image_sourcing: unexpected error for '{name}': {e}")

    if sourced:
        Logger.info(f"image_sourcing: found images for {len(sourced)}/{len(comedian_names)} new comedians")
    return sourced
