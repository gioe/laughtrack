"""HTML extraction for BookTix box-office pages.

Two-step source:
  1. The box office home (``https://{org}.booktix.com/dept/main``) links each
     production as ``/dept/main/e/{code}`` — ``extract_event_urls`` returns the
     absolute production URLs.
  2. Each production page is server-rendered HTML — ``extract_events`` reads the
     production name (the ``<h3 class="text-2xl font-bold ...">`` heading) and
     every showtime ("Sat Jun 20 2026 - 7:00 PM") plus the ticket price,
     producing one ``BookTixEvent`` per showtime.

No JSON-LD or public JSON API is exposed, so parsing is HTML-based.
"""

import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.booktix import BookTixEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.number import parse_price_text

# Production codes link as /dept/main/e/{code} on the box office home.
_EVENT_CODE_RE = re.compile(r"/dept/main/e/([A-Za-z0-9_-]+)")

# Showtime, e.g. "Sat Jun 20 2026 - 7:00 PM".
_SHOWTIME_RE = re.compile(
    r"(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat) [A-Z][a-z]{2} \d{1,2} \d{4} - \d{1,2}:\d{2} (?:AM|PM)"
)


def extract_event_urls(home_html: str, base_url: str) -> List[str]:
    """Return absolute BookTix production URLs from the box office home HTML.

    ``base_url`` is the box office origin, e.g. ``https://makeshift.booktix.com``.
    Codes are de-duplicated, preserving first-seen order.
    """
    if not home_html:
        return []
    seen: set = set()
    codes: List[str] = []
    for code in _EVENT_CODE_RE.findall(home_html):
        if code not in seen:
            seen.add(code)
            codes.append(code)
    return [urljoin(base_url, f"/dept/main/e/{code}") for code in codes]


def _extract_price(html: str) -> Optional[float]:
    """Return the lowest dollar price on the page, or None if none present."""
    # detect_free=False: this scans the whole page HTML, where an incidental
    # "free" (e.g. "free parking") must not zero out a real price.
    return parse_price_text(html, detect_free=False)


def extract_events(detail_html: str, detail_url: str) -> List[BookTixEvent]:
    """Extract one BookTixEvent per showtime from a BookTix production page."""
    if not detail_html:
        return []

    soup = BeautifulSoup(detail_html, "html.parser")

    # The production name is the bold display heading on the page.
    name_el = soup.select_one("h3.text-2xl.font-bold")
    title = name_el.get_text(strip=True) if name_el else ""
    if not title:
        Logger.debug(f"BookTixExtractor: no production name on {detail_url}")
        return []

    showtimes = list(dict.fromkeys(_SHOWTIME_RE.findall(detail_html)))
    if not showtimes:
        Logger.debug(f"BookTixExtractor: no showtimes for '{title}' on {detail_url}")
        return []

    price = _extract_price(detail_html)

    return [
        BookTixEvent(
            title=title,
            start_date_str=showtime,
            ticket_url=detail_url,
            price=price,
        )
        for showtime in showtimes
    ]
