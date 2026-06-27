"""HTML extraction for the Coral Springs Center for the Arts venue scraper.

Two phases:

1. :meth:`extract_comedy_detail_urls` parses the server-rendered, category-filtered
   comedy listing (``/events/category/comedy``) into the set of per-event detail
   page URLs. The listing is already comedy-only (the venue's CMS filters
   server-side), so no keyword filtering is applied here.
2. :meth:`parse_detail` parses one ``/events/detail/<slug>`` page — the source of
   truth for the title (``<h1 class="title">``), the full date (the
   ``m-date__month`` / ``m-date__day`` / ``m-date__year`` spans), the showtime and
   the eVenue buy link.
"""

import html as _html
import re
from datetime import date, datetime
from typing import List, Optional

from laughtrack.core.entities.event.coral_springs_center import (
    CoralSpringsCenterEvent,
)
from laughtrack.foundation.infrastructure.logger.logger import Logger

_DETAIL_PATH_RE = re.compile(r'/events/detail/[a-z0-9][a-z0-9-]*', re.IGNORECASE)
_H1_TITLE_RE = re.compile(r'<h1[^>]*class="title"[^>]*>(.*?)</h1>', re.IGNORECASE | re.DOTALL)
_MONTH_RE = re.compile(r'class="m-date__month"[^>]*>\s*([A-Za-z]{3,9})', re.IGNORECASE)
_DAY_RE = re.compile(r'class="m-date__day"[^>]*>\s*(\d{1,2})', re.IGNORECASE)
_YEAR_RE = re.compile(r'class="m-date__year"[^>]*>\s*,?\s*(\d{4})', re.IGNORECASE)
_TIME_RE = re.compile(r'(\d{1,2}:\d{2}\s*[AP]M)', re.IGNORECASE)
_TICKET_RE = re.compile(
    r'https://thecenter\.evenue\.net/cgi-bin/ncommerce3/SEGetEventInfo\?[^"\'<>\s]+',
    re.IGNORECASE,
)
_TAG_RE = re.compile(r'<[^>]+>')

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _extract_showtime(detail_html: str, default: str = "7:30PM") -> str:
    """Return the most likely SHOW time on a detail page.

    The CMS repeats the show time across the title, date line and buy button
    while listing the doors time at most once, so the most-frequent time is the
    show time. This is more robust than first/last-match, which would pick the
    doors time whenever it happens to appear first.
    """
    times = [re.sub(r'\s+', '', t).upper() for t in _TIME_RE.findall(detail_html)]
    if not times:
        return default
    counts: dict = {}
    for t in times:
        counts[t] = counts.get(t, 0) + 1
    # Highest count wins; ties broken by first appearance order.
    return max(times, key=lambda t: (counts[t], -times.index(t)))


class CoralSpringsCenterExtractor:
    """Pure HTML parsing for Coral Springs Center for the Arts."""

    @staticmethod
    def extract_comedy_detail_urls(listing_html: str, base_url: str) -> List[str]:
        """Return absolute detail-page URLs from the comedy-category listing."""
        origin = re.match(r'https?://[^/]+', base_url)
        prefix = origin.group(0) if origin else "https://www.thecentercs.com"

        seen: set = set()
        urls: List[str] = []
        for path in _DETAIL_PATH_RE.findall(listing_html or ""):
            url = f"{prefix}{path}"
            if url not in seen:
                seen.add(url)
                urls.append(url)
        return urls

    @staticmethod
    def parse_detail(detail_html: str, detail_url: str) -> Optional[CoralSpringsCenterEvent]:
        """Parse a single detail page into an event, or None if unparseable/past."""
        if not detail_html:
            return None

        title_match = _H1_TITLE_RE.search(detail_html)
        if not title_match:
            return None
        name = _html.unescape(_TAG_RE.sub('', title_match.group(1))).strip()
        if not name:
            return None

        month_match = _MONTH_RE.search(detail_html)
        day_match = _DAY_RE.search(detail_html)
        year_match = _YEAR_RE.search(detail_html)
        if not (month_match and day_match and year_match):
            return None

        month = _MONTHS.get(month_match.group(1)[:3].lower())
        if not month:
            return None
        try:
            event_date = date(int(year_match.group(1)), month, int(day_match.group(1)))
        except ValueError:
            return None

        # Skip past events (the listing is already upcoming, but be defensive).
        if event_date < datetime.now().date():
            return None

        start_time = _extract_showtime(detail_html)

        ticket_match = _TICKET_RE.search(detail_html)
        ticket_url = _html.unescape(ticket_match.group(0)) if ticket_match else None

        return CoralSpringsCenterEvent(
            name=name,
            start_date=event_date.isoformat(),
            start_time=start_time,
            detail_url=detail_url,
            ticket_url=ticket_url,
        )

    @staticmethod
    def extract_events(
        listing_html: str,
        base_url: str,
        detail_pages: dict,
    ) -> List[CoralSpringsCenterEvent]:
        """Build events from the listing + a {detail_url: html} map (test entrypoint)."""
        events: List[CoralSpringsCenterEvent] = []
        for url in CoralSpringsCenterExtractor.extract_comedy_detail_urls(listing_html, base_url):
            html_content = detail_pages.get(url)
            if not html_content:
                Logger.warn(f"CoralSpringsCenterExtractor: no detail HTML for {url}")
                continue
            event = CoralSpringsCenterExtractor.parse_detail(html_content, url)
            if event is not None:
                events.append(event)
        return events
