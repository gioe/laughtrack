"""URL discovery for the TicketsCandy scraper.

TicketsCandy is a ticketing platform; venues link out to it from their own
sites. There is no TicketsCandy organizer/venue aggregation endpoint, so the
upcoming-event URLs are discovered by crawling the venue's own listing (and, for
two-hop sites like Funny Pharm's WordPress, the per-show sub-pages) and
collecting every ``ticketscandy.com/e/<slug>`` link.
"""

import re
from typing import List, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# Matches a TicketsCandy event URL on any TicketsCandy host (with or without a
# leading subdomain), e.g. https://ticketscandy.com/e/<slug>-<id>.
_TICKETSCANDY_EVENT_RE = re.compile(
    r"https?://(?:[a-z0-9-]+\.)*ticketscandy\.com/e/[A-Za-z0-9/_-]+",
    re.IGNORECASE,
)


class TicketsCandyExtractor:
    """Finds TicketsCandy event links and same-host crawl targets in HTML."""

    @staticmethod
    def extract_event_urls(html: str) -> Set[str]:
        """Return every ``ticketscandy.com/e/...`` URL found in the HTML.

        Trailing punctuation from HTML-entity-encoded hrefs is stripped.
        """
        if not html:
            return set()
        return {url.rstrip('".,)') for url in _TICKETSCANDY_EVENT_RE.findall(html)}

    @staticmethod
    def extract_subpage_urls(html: str, base_url: str, path_prefix: str) -> List[str]:
        """Same-host links whose path starts with ``path_prefix`` (the per-show
        detail pages to crawl for TicketsCandy links).

        Excludes the listing page itself (``base_url``) and any link whose path
        is exactly the prefix, so only deeper sub-pages are returned.
        """
        if not html:
            return []
        base = urlparse(base_url)
        prefix = path_prefix.rstrip("/") + "/"
        seen: Set[str] = set()
        out: List[str] = []
        for anchor in BeautifulSoup(html, "html.parser").find_all("a", href=True):
            parsed = urlparse(urljoin(base_url, anchor["href"]))
            if parsed.netloc != base.netloc:
                continue
            if not parsed.path.startswith(prefix):
                continue
            if parsed.path.rstrip("/") == prefix.rstrip("/"):
                continue
            normalized = f"{parsed.scheme or 'https'}://{parsed.netloc}{parsed.path}"
            if normalized not in seen:
                seen.add(normalized)
                out.append(normalized)
        return out
