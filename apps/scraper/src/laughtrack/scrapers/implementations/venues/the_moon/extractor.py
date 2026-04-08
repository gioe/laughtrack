"""HTML extraction for The Moon (Tallahassee) listing pages."""

import re
from html import unescape
from typing import List, Optional

from laughtrack.core.entities.event.the_moon import TheMoonEvent
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


def _strip_tags(text: str) -> str:
    """Remove all HTML tags from *text* and decode HTML entities."""
    return unescape(re.sub(r"<[^>]+>", "", text)).strip()


class TheMoonExtractor:
    """
    Parses HTML from The Moon's event listing page.

    The site uses the ``rhp-events`` WordPress plugin which renders each
    show inside a ``div.eventWrapper.rhpSingleEvent`` block.
    """

    @staticmethod
    def extract_events(html: str) -> List[TheMoonEvent]:
        """Extract all event cards from a single listing page."""
        if not html:
            return []

        events: List[TheMoonEvent] = []
        cards = html.split(_CARD_SPLIT)

        for card in cards[1:]:  # first segment is preamble, not an event
            event = TheMoonExtractor._parse_card(card)
            if event is not None:
                events.append(event)

        return events

    @staticmethod
    def _parse_card(card_html: str) -> Optional[TheMoonEvent]:
        """Parse a single event card fragment and return a TheMoonEvent."""
        title_m = _TITLE_RE.search(card_html)
        date_m = _DATE_RE.search(card_html)
        time_m = _TIME_RE.search(card_html)
        ticket_m = _TICKET_RE.search(card_html)

        if not (title_m and date_m and ticket_m):
            Logger.debug(
                "TheMoonExtractor: skipping card — missing title, date, or ticket URL"
            )
            return None

        title = _strip_tags(title_m.group(1))
        date_str = _strip_tags(date_m.group(1))
        time_str = _strip_tags(time_m.group(1)) if time_m else ""
        ticket_url = ticket_m.group(1)

        if not title or not date_str or not ticket_url:
            return None

        return TheMoonEvent(
            title=title,
            date_str=date_str,
            time_str=time_str,
            ticket_url=ticket_url,
        )
