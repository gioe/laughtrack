"""
Detects tour/shows/events subpage links on comedian homepages.

Scans <a> elements for hrefs matching common tour-page patterns
(e.g. /tour, /shows, /events, /dates, /schedule, /tour-dates, /live).
Returns deduplicated absolute URLs for further scraping.
"""

import re
from typing import List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


# Patterns that match common tour/show subpage paths.
# Anchored to path segments to avoid false positives (e.g. /about-shows).
_TOUR_PATH_RE = re.compile(
    r"^/(tour|tours|shows|events|dates|schedule|tour-dates|live|performances|upcoming|concerts)/?$",
    re.IGNORECASE,
)


def detect_tour_links(html: str, base_url: str) -> List[str]:
    """Return deduplicated absolute URLs of tour/show subpages found in *html*.

    Only returns links that are on the same domain as *base_url* (to avoid
    following external links to ticketing sites, social media, etc.).
    """
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc.lower().lstrip("www.")

    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    result: list[str] = []

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if not isinstance(href, str) or not href.strip():
            continue
        href = href.strip()

        # Build absolute URL
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)

        # Only follow same-domain links
        link_domain = parsed.netloc.lower().lstrip("www.")
        if link_domain != base_domain:
            continue

        # Check if the path matches a tour-page pattern
        # Normalize: ensure leading slash, strip trailing slash, then match
        normalized_path = "/" + parsed.path.strip("/")
        if not _TOUR_PATH_RE.match(normalized_path):
            continue

        # Deduplicate by scheme+netloc+path (ignore query/fragment)
        canonical = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        if canonical in seen:
            continue
        seen.add(canonical)
        result.append(absolute)

    return result
