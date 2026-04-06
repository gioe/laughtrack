"""
Detects Bandsintown and Songkick embedded widgets in comedian website HTML
and extracts artist identifiers for use by TourDatesScraper.

Bandsintown widgets use:
  <div class="bit-widget-initializer" data-artist-name="Artist Name" ...>
  or data-artist-id="12345"
  or <script src="https://widget.bandsintown.com/..." data-artist-name="Artist Name">
  or <a href="https://www.bandsintown.com/artist-slug">

Songkick widgets use:
  <a class="songkick-widget" href="https://www.songkick.com/artists/ARTIST_ID-slug" ...>
  or data-songkick-id="ARTIST_ID"
"""

import re
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup


@dataclass
class WidgetResult:
    """Extraction result from widget detection."""
    bandsintown_id: Optional[str] = None
    songkick_id: Optional[str] = None

    @property
    def has_any(self) -> bool:
        return self.bandsintown_id is not None or self.songkick_id is not None


# Regex to extract Songkick artist numeric ID from URLs like:
#   https://www.songkick.com/artists/12345-artist-name
_SONGKICK_ARTIST_URL_RE = re.compile(
    r"songkick\.com/artists/(\d+)", re.IGNORECASE
)

# Regex to extract Bandsintown artist slug or numeric ID from profile URLs like:
#   https://www.bandsintown.com/mark-normand
#   https://www.bandsintown.com/a/12345
# Excludes utility paths (privacy, terms, login, etc.)
_BIT_PROFILE_URL_RE = re.compile(
    r"bandsintown\.com/(?:a/(\d+)|([a-zA-Z0-9][a-zA-Z0-9._-]+))\s*[\"']",
    re.IGNORECASE,
)
_BIT_PROFILE_EXCLUDE = frozenset({
    "privacy", "terms", "signup", "login", "support", "about",
    "c", "e", "f", "festivals", "apps", "blog",
})


def detect_widgets(html: str) -> WidgetResult:
    """Parse HTML and return any Bandsintown/Songkick artist identifiers found."""
    soup = BeautifulSoup(html, "html.parser")
    return WidgetResult(
        bandsintown_id=_detect_bandsintown(soup, html),
        songkick_id=_detect_songkick(soup, html),
    )


def _detect_bandsintown(soup: BeautifulSoup, html: str) -> Optional[str]:
    """Detect Bandsintown widget and extract artist name or ID."""
    # Primary: <div class="bit-widget-initializer" data-artist-name="...">
    widget = soup.find(class_="bit-widget-initializer")
    if widget:
        artist = widget.get("data-artist-name")
        if artist and isinstance(artist, str) and artist.strip():
            return artist.strip()
        artist_id = widget.get("data-artist-id")
        if artist_id and isinstance(artist_id, str) and artist_id.strip():
            return artist_id.strip()

    # Fallback: any element with data-bit-artist attribute
    el = soup.find(attrs={"data-bit-artist": True})
    if el:
        val = el["data-bit-artist"]
        if isinstance(val, str) and val.strip():
            return val.strip()

    # Fallback: <script src="https://widget.bandsintown.com/..."> with data attributes
    for script in soup.find_all("script", src=True):
        src = script.get("src", "")
        if isinstance(src, str) and "widget.bandsintown.com" in src.lower():
            artist = script.get("data-artist-name")
            if artist and isinstance(artist, str) and artist.strip():
                return artist.strip()
            artist_id = script.get("data-artist-id")
            if artist_id and isinstance(artist_id, str) and artist_id.strip():
                return artist_id.strip()

    # Fallback: bandsintown.com profile link anywhere in page HTML
    for m in _BIT_PROFILE_URL_RE.finditer(html):
        numeric_id = m.group(1)
        if numeric_id:
            return numeric_id
        slug = m.group(2)
        if slug and slug.lower() not in _BIT_PROFILE_EXCLUDE:
            return slug

    return None


def _detect_songkick(soup: BeautifulSoup, html: str) -> Optional[str]:
    """Detect Songkick widget and extract artist numeric ID."""
    # Primary: <a class="songkick-widget" href="...songkick.com/artists/ID-slug">
    widget = soup.find(class_="songkick-widget")
    if widget:
        href = widget.get("href", "")
        if isinstance(href, str):
            m = _SONGKICK_ARTIST_URL_RE.search(href)
            if m:
                return m.group(1)
        # data-songkick-id attribute
        sk_id = widget.get("data-songkick-id")
        if sk_id and isinstance(sk_id, str) and sk_id.strip():
            return sk_id.strip()

    # Fallback: any element with data-songkick-id
    el = soup.find(attrs={"data-songkick-id": True})
    if el:
        val = el["data-songkick-id"]
        if isinstance(val, str) and val.strip():
            return val.strip()

    # Fallback: Songkick artist URL anywhere in the page (e.g. in script tags)
    m = _SONGKICK_ARTIST_URL_RE.search(html)
    if m:
        return m.group(1)

    return None
