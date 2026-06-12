"""HTML extraction for The Comedy & Magic Club listing pages."""

import re
from typing import List, Optional

from laughtrack.core.entities.event.comedy_magic_club import ComedyMagicClubEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.html.utils import HtmlUtils

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
# Cost text rendered by the rhp-events plugin (TASK-2842), e.g. "$27" or
# "$27 - $37". Same markup family the Funny Bone Rockhouse parser reads
# (_funny_bone_ticket_price in api/etix/scraper.py).
_COST_RE = re.compile(
    r'rhp-event__cost-text--(?:list|grid)[^>]*>\s*(.*?)\s*</span>',
    re.DOTALL | re.IGNORECASE,
)
_PRICE_AMOUNT_RE = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)")


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

        title = HtmlUtils.strip_tags(title_m.group(1))
        date_str = HtmlUtils.strip_tags(date_m.group(1))
        time_str = HtmlUtils.strip_tags(time_m.group(1)) if time_m else ""
        ticket_url = ticket_m.group(1)

        if not title or not date_str or not ticket_url:
            return None

        return ComedyMagicClubEvent(
            title=title,
            date_str=date_str,
            time_str=time_str,
            ticket_url=ticket_url,
            price=ComedyMagicClubExtractor._parse_cost(card_html),
        )

    @staticmethod
    def _parse_cost(card_html: str) -> Optional[float]:
        """Parse the card's rhp-event cost text into the lowest dollar amount.

        Ranges like "$27 - $37" take the low end; a missing cost element or a
        text without a parseable positive amount yields None (price unknown —
        a $0 in marketing copy is not proof the show is free).
        """
        cost_m = _COST_RE.search(card_html)
        if not cost_m:
            return None

        amounts = []
        for raw in _PRICE_AMOUNT_RE.findall(HtmlUtils.strip_tags(cost_m.group(1))):
            try:
                amounts.append(float(raw))
            except ValueError:
                continue

        positive = [a for a in amounts if a > 0]
        return min(positive) if positive else None
