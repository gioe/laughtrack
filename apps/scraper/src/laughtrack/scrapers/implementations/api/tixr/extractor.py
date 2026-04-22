"""Generic Tixr URL extraction and pagination utilities."""

import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from laughtrack.foundation.utilities.json.utils import JSONUtils
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper


class TixrExtractor:
    """Extracts Tixr event URLs (short and long form) from calendar page HTML."""

    # Short form: https://tixr.com/e/{id}
    _SHORT_URL_RE = re.compile(
        r'https?://(?:www\.)?tixr\.com/e/(\d+)',
        re.IGNORECASE,
    )

    # Long form: https://www.tixr.com/groups/{group}/events/{slug}-{id}
    # Captured as the full URL; client handles --{id} (won't-fix) skipping.
    _LONG_URL_RE = re.compile(
        r'https?://(?:www\.)?tixr\.com/groups/[^\s"\'<>]+/events/[^\s"\'<>]+',
        re.IGNORECASE,
    )

    # Subdomain form: https://{group}.tixr.com/{slug}
    # Some venues embed links as {group}.tixr.com/{slug} which 301-redirect to
    # tixr.com/groups/{group}/{slug}. Exclude "www" subdomain (handled above)
    # and bare group-page links (no slug after the domain).
    _SUBDOMAIN_URL_RE = re.compile(
        r'https?://(?!www\.)[a-z0-9-]+\.tixr\.com/([^\s"\'<>]+)',
        re.IGNORECASE,
    )

    # Extracts the trailing numeric event ID from a long-form URL slug.
    # Matches the final -\d+ sequence (single-dash format with a digit ID).
    _LONG_URL_ID_RE = re.compile(r'-(\d+)$')

    _PAGINATION_HINTS: tuple[str, ...] = (
        "more shows",
        "next month",
        "next",
        "older",
        "load more",
    )

    @staticmethod
    def extract_tixr_urls(html_content: str) -> List[str]:
        """
        Extract all unique Tixr event URLs from calendar page HTML.

        Handles both short form (tixr.com/e/{id}) and long form
        (tixr.com/groups/*/events/*-{id}). Results are deduplicated
        by event ID across both forms — if the same event appears as
        both a short and long URL, only the short form is returned.
        Short-form URLs are returned first (in document order), followed
        by long-form URLs not already represented by a short-form link.

        Args:
            html_content: HTML content of a venue calendar page

        Returns:
            List of unique Tixr event URLs
        """
        seen_ids: set = set()
        seen_urls: set = set()
        urls: List[str] = []

        for match in TixrExtractor._SHORT_URL_RE.finditer(html_content):
            event_id = match.group(1)
            url = f"https://tixr.com/e/{event_id}"
            if event_id not in seen_ids:
                seen_ids.add(event_id)
                seen_urls.add(url)
                urls.append(url)

        for match in TixrExtractor._LONG_URL_RE.finditer(html_content):
            url = match.group(0)
            if url in seen_urls:
                continue
            id_match = TixrExtractor._LONG_URL_ID_RE.search(url)
            event_id = id_match.group(1) if id_match else None
            if event_id is None or event_id not in seen_ids:
                if event_id:
                    seen_ids.add(event_id)
                seen_urls.add(url)
                urls.append(url)

        # Subdomain form: {group}.tixr.com/{slug} — these 301-redirect to
        # tixr.com/groups/{group}/{slug}. Include them as-is; the Tixr client
        # follows redirects when fetching event pages.
        for match in TixrExtractor._SUBDOMAIN_URL_RE.finditer(html_content):
            url = match.group(0)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            urls.append(url)

        return urls

    @staticmethod
    def get_event_id(url: str) -> Optional[str]:
        """
        Extract the numeric event ID from any Tixr event URL.

        Handles both short form (tixr.com/e/{id}) and long form
        (tixr.com/groups/.../events/slug-{id}).  Returns None when
        no numeric ID can be parsed (e.g. double-dash --{id} URLs
        or non-Tixr URLs).

        Args:
            url: A Tixr event URL in short or long form

        Returns:
            Numeric event ID string, or None if not parseable
        """
        short_match = TixrExtractor._SHORT_URL_RE.search(url)
        if short_match:
            return short_match.group(1)
        long_match = TixrExtractor._LONG_URL_ID_RE.search(url)
        if long_match:
            return long_match.group(1)
        return None

    @staticmethod
    def extract_org_jsonld_event_urls(html_content: str) -> List[str]:
        """
        Extract event URLs from the Organization JSON-LD block on a Tixr group page.

        Tixr embeds an Organization schema block listing the group's featured events,
        each with a startDate.  These are the only events that also have server-rendered
        JSON-LD on their individual pages.  Events in the HTML list that aren't in the
        Org JSON-LD use client-side rendering with no static date data and would
        produce batch failures with no recoverable information.

        Args:
            html_content: HTML of a Tixr group page

        Returns:
            List of event page URLs found in the Organization JSON-LD events array,
            or [] if the block is absent, unparseable, or present but contains no
            events with a 'url' key.  Callers must treat [] as "no usable Org JSON-LD"
            and fall back to all HTML-extracted URLs in that case.
        """
        urls: List[str] = []
        blocks = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html_content,
            re.DOTALL | re.IGNORECASE,
        )
        for item in JSONUtils.parse_json_ld_contents(blocks):
            if not isinstance(item, dict) or item.get("@type") != "Organization":
                continue
            for event in item.get("events", []):
                if isinstance(event, dict) and event.get("url"):
                    urls.append(event["url"])
        return urls

    @staticmethod
    def extract_pagination_urls(html_content: str, base_url: str) -> List[str]:
        """
        Extract likely pagination URLs from a venue calendar page.

        This is intentionally conservative: it follows same-site navigation that
        looks like "more shows" / "next month" style pagination, and excludes
        Tixr event-detail URLs so the discovery phase cannot wander into the
        blocked detail pages.
        """
        candidates: List[str] = []
        seen: set[str] = set()
        base_netloc = urlparse(base_url).netloc.lower()

        def add_candidate(href: Optional[str]) -> None:
            if not href:
                return
            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)
            if parsed.netloc.lower() != base_netloc:
                return
            if "/events/" in parsed.path:
                return
            if absolute not in seen:
                seen.add(absolute)
                candidates.append(absolute)

        for link in HtmlScraper.find_elements_by_selector(
            html_content, "a.btn.btn-outline-light.loading-btn[href]"
        ):
            add_candidate(getattr(link, "get", lambda *_: None)("href"))

        for link in HtmlScraper.find_elements(html_content, "a", href=True):
            href = getattr(link, "get", lambda *_: None)("href")
            title = str(getattr(link, "get", lambda *_: None)("title") or "").lower()
            aria_label = str(getattr(link, "get", lambda *_: None)("aria-label") or "").lower()
            rel = " ".join(getattr(link, "get", lambda *_: None)("rel") or []).lower()
            text = str(getattr(link, "get_text", lambda **_: "")(strip=True) or "").lower()

            hint_text = " ".join(part for part in (title, aria_label, rel, text) if part)
            if any(hint in hint_text for hint in TixrExtractor._PAGINATION_HINTS):
                add_candidate(href)

        for icon in HtmlScraper.find_elements(html_content, "i", class_="fas fa-caret-right"):
            parent = getattr(icon, "find_parent", lambda *_: None)("a")
            if parent is not None:
                add_candidate(getattr(parent, "get", lambda *_: None)("href"))

        return candidates
