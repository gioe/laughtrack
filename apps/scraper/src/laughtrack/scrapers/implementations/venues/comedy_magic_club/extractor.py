"""HTML extraction for The Comedy & Magic Club listing pages."""

import re
from html import unescape
from typing import List, Optional

from laughtrack.core.entities.event.comedy_magic_club import ComedyMagicClubEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# Each event card begins immediately after this comment in the HTML.
_CARD_SPLIT = "<!-- Event List Wrapper -->"

# Selectors / patterns targeting the rhp-events plugin's rendered output.
_TITLE_RE = re.compile(
    r'<h2[^>]*rhp-event__title[^>]*>\s*(.*?)\s*</h2>', re.DOTALL | re.IGNORECASE
)
_DATE_RE = re.compile(
    r'singleEventDate[^>]*>\s*(.*?)\s*</div>', re.DOTALL | re.IGNORECASE
)
_TIME_RE = re.compile(
    r'rhp-event__time-text[^>]*>\s*(.*?)\s*</span>', re.DOTALL | re.IGNORECASE
)
_TICKET_RE = re.compile(
    r'href="(https://www\.etix\.com/[^"]+)"', re.IGNORECASE
)
_PAGE_RE = re.compile(
    r'events/page/(\d+)/', re.IGNORECASE
)


def _strip_tags(text: str) -> str:
    """Remove all HTML tags from *text* and decode HTML entities."""
    return unescape(re.sub(r"<[^>]+>", "", text)).strip()


class ComedyMagicClubExtractor:
    """
    Parses HTML from The Comedy & Magic Club's event listing pages.

    The site uses the ``rhp-events`` WordPress plugin which renders each
    show inside a ``div.eventWrapper.rhpSingleEvent`` block.  The listing
    page does *not* include the year in the date string; year inference is
    delegated to ``ComedyMagicClubEvent.to_show()``.
    """

    @staticmethod
    def extract_events(html: str) -> List[ComedyMagicClubEvent]:
        """Extract all event cards from a single listing page."""
        if not html:
            return []

        events: List[ComedyMagicClubEvent] = []
        cards = html.split(_CARD_SPLIT)

        for card in cards[1:]:  # first segment is preamble, not an event
            event = ComedyMagicClubExtractor._parse_card(card)
            if event is not None:
                events.append(event)

        return events

    @staticmethod
    def get_max_page(html: str) -> int:
        """
        Return the highest page number found in pagination links.

        Returns 1 if no pagination links are present (single-page listing).
        """
        pages = _PAGE_RE.findall(html)
        return max((int(p) for p in pages), default=1)

    @staticmethod
    def _parse_card(card_html: str) -> Optional[ComedyMagicClubEvent]:
        """Parse a single event card fragment and return a ComedyMagicClubEvent."""
        title_m = _TITLE_RE.search(card_html)
        date_m = _DATE_RE.search(card_html)
        time_m = _TIME_RE.search(card_html)
        ticket_m = _TICKET_RE.search(card_html)

        if not (title_m and date_m and ticket_m):
            Logger.debug(
                "ComedyMagicClubExtractor: skipping card — missing title, date, or ticket URL"
            )
            return None

        title = _strip_tags(title_m.group(1))
        date_str = _strip_tags(date_m.group(1))
        time_str = _strip_tags(time_m.group(1)) if time_m else ""
        ticket_url = ticket_m.group(1)

        if not title or not date_str or not ticket_url:
            return None

        return ComedyMagicClubEvent(
            title=title,
            date_str=date_str,
            time_str=time_str,
            ticket_url=ticket_url,
        )
