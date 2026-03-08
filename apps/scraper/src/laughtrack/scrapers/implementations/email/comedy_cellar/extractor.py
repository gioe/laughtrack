"""
Comedy Cellar email newsletter extractor.

Parses HTML newsletters sent from comedycellar.com and returns a list of
EmailShowEvent objects — one per show listing found in the email.

Typical Comedy Cellar newsletter structure:

    <div class="show-block">
      <p class="show-date">Friday, March 7, 2026 - 8:00 PM</p>
      <p class="headliner">Dave Chappelle</p>
      <a href="https://www.comedycellar.com/reservations-newyork/?showid=12345">
        Reserve Now
      </a>
    </div>

The extractor is intentionally liberal: it first tries CSS-class-based
selectors and falls back to heuristic link/text scanning so it can handle
variations in newsletter design across marketing campaigns.
"""

import re
from datetime import datetime, timezone
from typing import List, Optional

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.email_show_event import EmailShowEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.datetime import DateTimeUtils

_VENUE_TIMEZONE = "America/New_York"
_TICKET_DOMAIN = "comedycellar.com"

# Date/time patterns found in Comedy Cellar newsletters.
_DATE_PATTERNS = [
    # "Friday, March 7, 2026 - 8:00 PM"
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+"
    r"(\w+ \d{1,2},?\s+\d{4})\s*[-–]\s*(\d{1,2}:\d{2}\s*(?:AM|PM))",
    # "March 7, 2026 8:00 PM"
    r"(\w+ \d{1,2},?\s+\d{4})\s+(\d{1,2}:\d{2}\s*(?:AM|PM))",
]
_DATE_FORMATS = ["%B %d %Y %I:%M %p", "%B %d, %Y %I:%M %p"]


class ComedyCellarEmailExtractor:
    """Extract show listings from a Comedy Cellar email newsletter."""

    def __init__(self, logger_context: Optional[dict] = None) -> None:
        self._ctx = logger_context or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, html_body: str) -> List[EmailShowEvent]:
        """
        Parse *html_body* and return all show listings found.

        Args:
            html_body: Raw HTML string from the email.

        Returns:
            List of EmailShowEvent objects; empty if none found.
        """
        soup = BeautifulSoup(html_body, "html.parser")
        events: List[EmailShowEvent] = []

        # Strategy 1: look for structured show blocks
        events = self._extract_from_show_blocks(soup)

        # Strategy 2: scan ticket links and infer surrounding context
        if not events:
            events = self._extract_from_ticket_links(soup)

        Logger.debug(
            f"[ComedyCellarEmailExtractor] Extracted {len(events)} events",
            self._ctx,
        )
        return events

    # ------------------------------------------------------------------
    # Strategy 1 – structured show blocks
    # ------------------------------------------------------------------

    def _extract_from_show_blocks(self, soup: BeautifulSoup) -> List[EmailShowEvent]:
        """Find elements that look like individual show listings."""
        events: List[EmailShowEvent] = []

        # Common container class names used in Comedy Cellar newsletters.
        selectors = [
            {"class": re.compile(r"show[-_]?block", re.I)},
            {"class": re.compile(r"show[-_]?listing", re.I)},
            {"class": re.compile(r"event[-_]?block", re.I)},
            {"class": re.compile(r"show[-_]?item", re.I)},
        ]

        containers: List[Tag] = []
        for attrs in selectors:
            containers = soup.find_all(True, attrs)
            if containers:
                break

        for block in containers:
            event = self._parse_show_block(block)
            if event:
                events.append(event)

        return events

    def _parse_show_block(self, block: Tag) -> Optional[EmailShowEvent]:
        """Parse a single show block element."""
        date = self._extract_date_from_block(block)
        headliner = self._extract_headliner_from_block(block)
        ticket_link = self._extract_ticket_link_from_tag(block)

        if not (date and headliner and ticket_link):
            return None

        return EmailShowEvent(date=date, headliner=headliner, ticket_link=ticket_link)

    # ------------------------------------------------------------------
    # Strategy 2 – ticket link scanning
    # ------------------------------------------------------------------

    def _extract_from_ticket_links(self, soup: BeautifulSoup) -> List[EmailShowEvent]:
        """Scan all links for reservation URLs and infer surrounding data."""
        events: List[EmailShowEvent] = []

        for anchor in soup.find_all("a", href=True):
            href: str = anchor["href"]
            if _TICKET_DOMAIN not in href:
                continue

            # Walk up the DOM to find the closest container with date + headliner.
            context = anchor.find_parent(["div", "td", "tr", "section", "article"]) or anchor
            date = self._extract_date_from_block(context)
            headliner = self._extract_headliner_from_block(context)

            if date and headliner:
                events.append(
                    EmailShowEvent(date=date, headliner=headliner, ticket_link=href)
                )

        return events

    # ------------------------------------------------------------------
    # Field extraction helpers
    # ------------------------------------------------------------------

    def _extract_date_from_block(self, tag: Tag) -> Optional[datetime]:
        """Try to parse a datetime from text inside *tag*."""
        text = tag.get_text(separator=" ", strip=True)
        return _parse_date_from_text(text)

    def _extract_headliner_from_block(self, tag: Tag) -> Optional[str]:
        """Return the headliner name found inside *tag*."""
        # Try explicit class names first.
        for cls_pattern in (r"headliner", r"comedian", r"performer", r"artist"):
            el = tag.find(True, {"class": re.compile(cls_pattern, re.I)})
            if el:
                name = el.get_text(strip=True)
                if name:
                    return name

        # Fallback: look for a <strong> or <b> that looks like a name.
        for el in tag.find_all(["strong", "b", "h3", "h4"]):
            text = el.get_text(strip=True)
            if text and len(text.split()) >= 2 and _looks_like_name(text):
                return text

        return None

    def _extract_ticket_link_from_tag(self, tag: Tag) -> Optional[str]:
        """Return the first Comedy Cellar reservation/ticket URL inside *tag*."""
        for anchor in tag.find_all("a", href=True):
            href: str = anchor["href"]
            if _TICKET_DOMAIN in href:
                return href
        return None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _parse_date_from_text(text: str) -> Optional[datetime]:
    """Attempt to extract and parse a show datetime from arbitrary text."""
    for pattern in _DATE_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            date_part = m.group(1).strip().rstrip(",")
            time_part = m.group(2).strip()
            combined = f"{date_part} {time_part}".upper()
            for fmt in _DATE_FORMATS:
                try:
                    return DateTimeUtils.parse_datetime_with_timezone(
                        f"{date_part} {time_part}", _VENUE_TIMEZONE
                    )
                except Exception:
                    pass
            # Manual fallback using strptime
            for fmt in _DATE_FORMATS:
                try:
                    naive = datetime.strptime(f"{date_part} {time_part}".strip(), fmt)
                    import pytz
                    tz = pytz.timezone(_VENUE_TIMEZONE)
                    return tz.localize(naive)
                except Exception:
                    continue
    return None


def _looks_like_name(text: str) -> bool:
    """Heuristic: return True if *text* could be a person's name."""
    # Reject strings that look like dates, times, or calls-to-action.
    lowered = text.lower()
    for skip in ("reserve", "buy", "ticket", "get", "click", "pm", "am", "show", "comedy"):
        if skip in lowered:
            return False
    # Require at least two capitalised words.
    words = text.split()
    return sum(1 for w in words if w and w[0].isupper()) >= 2
