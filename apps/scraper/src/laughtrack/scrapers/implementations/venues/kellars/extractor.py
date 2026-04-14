"""HTML extraction for Kellar's: Modern Magic and Comedy Club listing pages."""

import re
from html import unescape
from typing import List

from laughtrack.core.entities.event.kellars import KellarsEvent, parse_date_range
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Regex to match each event card: <a href="..." class="event-item">...</a>
_CARD_RE = re.compile(
    r'<a\s+href="(https://kellarsmagic\.com/tc-events/[^"]+)"'
    r'[^>]*class="event-item"[^>]*>(.*?)</a>',
    re.DOTALL,
)

_TITLE_RE = re.compile(r"<h2>(.*?)</h2>", re.DOTALL)
_SUBTITLE_RE = re.compile(r"<h4>(.*?)</h4>", re.DOTALL)
_DATE_RE = re.compile(
    r'class="medium-header event-date-range">(.*?)</p>', re.DOTALL
)
_TIME_RE = re.compile(
    r'class="small-header event-time">(.*?)</p>', re.DOTALL
)
_PRICE_RE = re.compile(r'class="event-price">(.*?)</p>', re.DOTALL)


def _strip_tags(text: str) -> str:
    """Remove all HTML tags from *text* and decode HTML entities."""
    return unescape(re.sub(r"<[^>]+>", "", text)).strip()


class KellarsExtractor:
    """
    Parses HTML from Kellar's /tc-events/ listing page.

    The site uses a WordPress Toolset Views layout with custom post type
    ``tc_events``.  Each show is an ``<a class="event-item">`` card
    containing performer name (h2), subtitle (h4), date range, time,
    and price.

    Multi-day date ranges are expanded here so each returned
    KellarsEvent represents a single show date.
    """

    @staticmethod
    def extract_events(html: str) -> List[KellarsEvent]:
        """Extract all event cards from a listing page, expanding date ranges."""
        if not html:
            return []

        events: List[KellarsEvent] = []

        for url, card_html in _CARD_RE.findall(html):
            title_m = _TITLE_RE.search(card_html)
            date_m = _DATE_RE.search(card_html)
            time_m = _TIME_RE.search(card_html)
            price_m = _PRICE_RE.search(card_html)
            subtitle_m = _SUBTITLE_RE.search(card_html)

            if not (title_m and date_m):
                Logger.debug(
                    f"KellarsExtractor: skipping card — missing title or date: {url}"
                )
                continue

            title = _strip_tags(title_m.group(1))
            date_str = _strip_tags(date_m.group(1))
            time_str = _strip_tags(time_m.group(1)) if time_m else ""
            price_str = _strip_tags(price_m.group(1)) if price_m else ""
            subtitle = _strip_tags(subtitle_m.group(1)) if subtitle_m else ""

            if not title or not date_str:
                continue

            # Expand multi-day date ranges into individual events
            dates = parse_date_range(date_str)
            if not dates:
                Logger.debug(
                    f"KellarsExtractor: could not parse date '{date_str}' for '{title}'"
                )
                continue

            for event_date in dates:
                events.append(
                    KellarsEvent(
                        title=title,
                        subtitle=subtitle,
                        event_date=event_date,
                        time_str=time_str,
                        price_str=price_str,
                        event_url=url,
                    )
                )

        return events
