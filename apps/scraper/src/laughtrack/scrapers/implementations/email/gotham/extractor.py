"""
Gotham Comedy Club email newsletter extractor.

Parses HTML newsletters sent from gothamcomedy.com and returns a list of
EmailShowEvent objects — one per show listing found in the email.

Typical Gotham Comedy Club newsletter structure:

    <table>
      <tr class="show-row">
        <td class="show-date">Saturday, March 8, 2026 - 8:00 PM</td>
        <td class="headliner">Jerry Seinfeld</td>
        <td>
          <a href="https://www.showclix.com/event/jerry-seinfeld-gotham">Get Tickets</a>
        </td>
      </tr>
    </table>

The extractor tries CSS-class-based row matching first, then falls back to
scanning ticket links and inferring surrounding context.
"""

import re
from datetime import datetime
from typing import List, Optional, Set

import pytz

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.email_show_event import EmailShowEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.datetime import DateTimeUtils

_VENUE_TIMEZONE = "America/New_York"
_TICKET_DOMAINS = ("gothamcomedy.com", "showclix.com")

_DATE_PATTERNS = [
    # "Saturday, March 8, 2026 - 8:00 PM"
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+"
    r"(\w+ \d{1,2},?\s+\d{4})\s*[-–]\s*(\d{1,2}:\d{2}\s*(?:AM|PM))",
    # "March 8, 2026 8:00 PM"
    r"(\w+ \d{1,2},?\s+\d{4})\s+(\d{1,2}:\d{2}\s*(?:AM|PM))",
]
_DATE_FORMATS = ["%B %d %Y %I:%M %p", "%B %d, %Y %I:%M %p"]


class GothamEmailExtractor:
    """Extract show listings from a Gotham Comedy Club email newsletter."""

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

        # Strategy 1: table row–based layout
        events = self._extract_from_table_rows(soup)

        # Strategy 2: block-based layout
        if not events:
            events = self._extract_from_show_blocks(soup)

        # Strategy 3: ticket link scanning
        if not events:
            events = self._extract_from_ticket_links(soup)

        Logger.debug(
            f"[GothamEmailExtractor] Extracted {len(events)} events",
            self._ctx,
        )
        return events

    # ------------------------------------------------------------------
    # Strategy 1 – table rows
    # ------------------------------------------------------------------

    def _extract_from_table_rows(self, soup: BeautifulSoup) -> List[EmailShowEvent]:
        """Parse show rows from a table-based newsletter layout."""
        events: List[EmailShowEvent] = []

        row_selectors = [
            {"class": re.compile(r"show[-_]?row", re.I)},
            {"class": re.compile(r"event[-_]?row", re.I)},
        ]

        rows: List[Tag] = []
        for attrs in row_selectors:
            rows = soup.find_all("tr", attrs)
            if rows:
                break

        for row in rows:
            event = self._parse_show_row(row)
            if event:
                events.append(event)

        return events

    def _parse_show_row(self, row: Tag) -> Optional[EmailShowEvent]:
        """Parse a <tr> element that contains one show listing."""
        cells = row.find_all("td")
        if not cells:
            return None

        date = self._extract_date_from_tag(row)
        headliner = self._extract_headliner_from_tag(row)
        ticket_link = self._extract_ticket_link_from_tag(row)

        if not (date and headliner and ticket_link):
            return None

        return EmailShowEvent(date=date, headliner=headliner, ticket_link=ticket_link)

    # ------------------------------------------------------------------
    # Strategy 2 – block-based layout
    # ------------------------------------------------------------------

    def _extract_from_show_blocks(self, soup: BeautifulSoup) -> List[EmailShowEvent]:
        """Find div/section elements that look like individual show listings."""
        events: List[EmailShowEvent] = []

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
        date = self._extract_date_from_tag(block)
        headliner = self._extract_headliner_from_tag(block)
        ticket_link = self._extract_ticket_link_from_tag(block)

        if not (date and headliner and ticket_link):
            return None

        return EmailShowEvent(date=date, headliner=headliner, ticket_link=ticket_link)

    # ------------------------------------------------------------------
    # Strategy 3 – ticket link scanning
    # ------------------------------------------------------------------

    def _extract_from_ticket_links(self, soup: BeautifulSoup) -> List[EmailShowEvent]:
        """Scan all links for ticket URLs and infer surrounding context."""
        events: List[EmailShowEvent] = []
        seen_urls: Set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href: str = anchor["href"]
            if not any(domain in href for domain in _TICKET_DOMAINS):
                continue
            if not href.startswith(("https://", "http://")):
                continue
            if href in seen_urls:
                continue

            context = anchor.find_parent(["div", "td", "tr", "section", "article"]) or anchor
            date = self._extract_date_from_tag(context)
            headliner = self._extract_headliner_from_tag(context)

            if date and headliner:
                seen_urls.add(href)
                events.append(
                    EmailShowEvent(date=date, headliner=headliner, ticket_link=href)
                )

        return events

    # ------------------------------------------------------------------
    # Field extraction helpers
    # ------------------------------------------------------------------

    def _extract_date_from_tag(self, tag: Tag) -> Optional[datetime]:
        text = tag.get_text(separator=" ", strip=True)
        return _parse_date_from_text(text)

    def _extract_headliner_from_tag(self, tag: Tag) -> Optional[str]:
        for cls_pattern in (r"headliner", r"comedian", r"performer", r"artist"):
            el = tag.find(True, {"class": re.compile(cls_pattern, re.I)})
            if el:
                name = el.get_text(strip=True)
                if name:
                    return name

        for el in tag.find_all(["strong", "b", "h3", "h4"]):
            text = el.get_text(strip=True)
            if text and len(text.split()) >= 2 and _looks_like_name(text):
                return text

        return None

    def _extract_ticket_link_from_tag(self, tag: Tag) -> Optional[str]:
        for anchor in tag.find_all("a", href=True):
            href: str = anchor["href"]
            if any(domain in href for domain in _TICKET_DOMAINS) and href.startswith(("https://", "http://")):
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
            try:
                return DateTimeUtils.parse_datetime_with_timezone(
                    f"{date_part} {time_part}", _VENUE_TIMEZONE
                )
            except Exception:
                pass
            for fmt in _DATE_FORMATS:
                try:
                    naive = datetime.strptime(f"{date_part} {time_part}".strip(), fmt)
                    tz = pytz.timezone(_VENUE_TIMEZONE)
                    return tz.localize(naive)
                except Exception:
                    continue
    return None


def _looks_like_name(text: str) -> bool:
    """Heuristic: return True if *text* could be a person's name."""
    lowered = text.lower()
    for skip in ("reserve", "buy", "ticket", "get", "click", "pm", "am", "show", "comedy", "gotham"):
        if skip in lowered:
            return False
    words = text.split()
    return sum(1 for w in words if w and w[0].isupper()) >= 2
