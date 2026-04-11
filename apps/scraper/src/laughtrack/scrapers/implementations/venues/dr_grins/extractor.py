"""HTML extraction for the Dr. Grins Etix venue page."""

import re
from datetime import date, datetime
from typing import List, Optional

from laughtrack.core.entities.event.dr_grins import DrGrinsEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Split on each <li> containing a performance card.
_CARD_RE = re.compile(
    r"<li>\s*<div\s+class=\"row\s+performance[^\"]*\".*?</li>", re.DOTALL
)

# Microdata ISO date (preferred).
_START_DATE_RE = re.compile(
    r'itemprop="startDate"[^>]*content="([^"]+)"', re.IGNORECASE
)

# Calendar fallback: month, date number.
_CAL_MONTH_RE = re.compile(r'class="month">([^<]+)</span>', re.IGNORECASE)
_CAL_DATE_RE = re.compile(r'class="date">(\d+)</span>', re.IGNORECASE)

# Title inside the performance-name heading.
_TITLE_RE = re.compile(
    r'<a\s+href="/ticket/p/[^"]+"\s*[^>]*>([^<]+)</a>', re.IGNORECASE
)

# Ticket URL.
_TICKET_RE = re.compile(r'href="(/ticket/p/\d+/[^"]+)"', re.IGNORECASE)

# Show time string.
_DATETIME_RE = re.compile(
    r'class="performance-datetime">\s*(.*?)\s*</div>', re.DOTALL | re.IGNORECASE
)

# Pagination: max page number from the pagination nav.
_PAGE_NUM_RE = re.compile(r"pageNumber=(\d+)")

# Month abbreviation → month number.
_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _calendar_to_iso(month_abbr: str, day_num: str) -> Optional[str]:
    """Convert calendar div month/day to an ISO date string (YYYY-MM-DD)."""
    month = _MONTHS.get(month_abbr.strip().lower()[:3])
    if not month:
        return None
    try:
        day = int(day_num.strip())
    except (ValueError, TypeError):
        return None

    today = date.today()
    for year in (today.year, today.year + 1):
        candidate = date(year, month, day)
        if candidate >= today:
            return candidate.isoformat()

    return date(today.year + 1, month, day).isoformat()


class DrGrinsExtractor:
    """Parses HTML from the Etix venue page for Dr. Grins."""

    @staticmethod
    def extract_events(html: str) -> List[DrGrinsEvent]:
        """Extract all event cards from a single page of results."""
        if not html:
            return []

        events: List[DrGrinsEvent] = []
        for card_match in _CARD_RE.finditer(html):
            card = card_match.group(0)
            event = DrGrinsExtractor._parse_card(card)
            if event is not None:
                events.append(event)

        return events

    @staticmethod
    def extract_max_page(html: str) -> int:
        """Return the highest page number from pagination links, or 1."""
        pages = _PAGE_NUM_RE.findall(html)
        if not pages:
            return 1
        return max(int(p) for p in pages)

    @staticmethod
    def _parse_card(card_html: str) -> Optional[DrGrinsEvent]:
        """Parse a single event card and return a DrGrinsEvent."""
        title_m = _TITLE_RE.search(card_html)
        ticket_m = _TICKET_RE.search(card_html)

        if not (title_m and ticket_m):
            return None

        title = title_m.group(1).strip()
        ticket_url = f"https://www.etix.com{ticket_m.group(1)}"

        # Date: prefer microdata, fall back to calendar div.
        start_date = None
        sd_m = _START_DATE_RE.search(card_html)
        if sd_m:
            start_date = sd_m.group(1)
        else:
            month_m = _CAL_MONTH_RE.search(card_html)
            date_m = _CAL_DATE_RE.search(card_html)
            if month_m and date_m:
                start_date = _calendar_to_iso(month_m.group(1), date_m.group(1))

        if not start_date:
            Logger.debug(
                f"DrGrinsExtractor: skipping card — no date for '{title}'"
            )
            return None

        # Time string.
        dt_m = _DATETIME_RE.search(card_html)
        time_str = dt_m.group(1).strip() if dt_m else ""

        return DrGrinsEvent(
            title=title,
            start_date=start_date,
            time_str=time_str,
            ticket_url=ticket_url,
        )
