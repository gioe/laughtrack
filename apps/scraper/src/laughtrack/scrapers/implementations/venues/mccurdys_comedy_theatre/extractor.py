"""
HTML extraction for McCurdy's Comedy Theatre pages.

Two page types are handled:

- Listing page (/shows/): grid of show cards, each linking to a detail page
  via onclick="location.href='/shows/show.cfm?shoID=<id>'" with the show
  title in an ``<h2 class="summary">`` tag.

- Detail page (/shows/show.cfm?shoID=<id>): show title in ``<h1 class="summary">``,
  performance dates under ``<div class="upcoming-shows-sidebar">`` as ``<li>``
  items, each containing a ``<p>`` with "Day, Month DD at H:MM PM" and an
  ``<a>`` linking to ``/shows/buy.cfm?timTicketID=<id>`` (which 302-redirects
  to ``https://www.etix.com/ticket/p/<id>``).
"""

import re
from typing import List

from laughtrack.core.entities.event.mccurdys_comedy_theatre import McCurdysEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


_ETIX_TICKET_BASE = "https://www.etix.com/ticket/p/"

# ---------------------------------------------------------------------------
# Listing-page patterns
# ---------------------------------------------------------------------------

_SHOW_LINK_RE = re.compile(
    r"onclick=\"location\.href='(/shows/show\.cfm\?shoID=\d+)';\"",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Detail-page patterns
# ---------------------------------------------------------------------------

_TITLE_RE = re.compile(r'<h1 class="summary">(.*?)</h1>', re.DOTALL | re.IGNORECASE)

# Each performance row: a <p> with "Day, Month DD at H:MM PM" and a buy link.
_PERFORMANCE_RE = re.compile(
    r"<p>\s*((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),"
    r"\s+\w+\s+\d{1,2}\s+at\s+\d{1,2}:\d{2}\s+[AP]M)\s*</p>"
    r".*?"
    r'buy\.cfm\?timTicketID=(\d+)',
    re.DOTALL | re.IGNORECASE,
)


class McCurdysExtractor:
    """Parses HTML from McCurdy's Comedy Theatre pages."""

    @staticmethod
    def extract_detail_page_urls(html: str, base_url: str) -> List[str]:
        """Extract unique show detail page URLs from the listing page."""
        if not html:
            return []
        paths = list(dict.fromkeys(_SHOW_LINK_RE.findall(html)))
        base = base_url.rstrip("/")
        # Ensure base is the site root, not the /shows/ subpath
        if "/shows" in base:
            base = base.rsplit("/shows", 1)[0]
        return [f"{base}{path}" for path in paths]

    @staticmethod
    def extract_events(html: str) -> List[McCurdysEvent]:
        """Extract all performances from a show detail page.

        Returns one McCurdysEvent per performance date/time listed on the page.
        A single show (e.g. "Jamie Lissow") typically has 3–5 performances
        across a weekend run.
        """
        if not html:
            return []

        title_m = _TITLE_RE.search(html)
        if not title_m:
            Logger.debug("McCurdysExtractor: no <h1 class='summary'> found")
            return []
        title = title_m.group(1).strip()
        if not title:
            return []

        events: List[McCurdysEvent] = []
        for m in _PERFORMANCE_RE.finditer(html):
            date_str = m.group(1).strip()
            ticket_id = m.group(2)
            ticket_url = f"{_ETIX_TICKET_BASE}{ticket_id}"
            events.append(McCurdysEvent(
                title=title,
                date_str=date_str,
                ticket_url=ticket_url,
            ))

        return events
