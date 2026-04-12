"""Extract event data from TicketWeb-powered club calendar pages.

Phase 1: Parse the inline `var all_events = [...]` JS array from the calendar page
         to discover event names, dates, and detail page URLs.
Phase 2: Parse each event detail page to extract the TicketWeb ticket purchase URL
         and sold-out status.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from laughtrack.core.entities.event.ticketweb import TicketWebEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class TicketWebExtractor:
    """Extracts event data from TicketWeb calendar widget HTML."""

    # Pattern to match the var all_events = [...] JS array
    _ALL_EVENTS_PATTERN = re.compile(
        r"var\s+all_events\s*=\s*\[(.*?)\];", re.DOTALL
    )

    # Patterns for individual event fields inside the JS object literals
    _TITLE_PATTERN = re.compile(r"title\s*:\s*'((?:[^'\\]|\\.)*)'")
    _START_PATTERN = re.compile(r"start\s*:\s*new\s+Date\s*\(\s*'([^']+)'\s*\)")
    _URL_PATTERN = re.compile(r"url\s*:\s*'((?:[^'\\]|\\.)*)'")

    # Pattern for TicketWeb buy button on detail pages
    _BUY_BUTTON_PATTERN = re.compile(
        r'<a[^>]*href="(https://www\.ticketweb\.com/event/[^"]+)"[^>]*class="[^"]*tw-buy-tix-btn[^"]*tw_(\w+)"[^>]*>',
        re.DOTALL,
    )

    # Broader fallback: any anchor with a ticketweb.com/event href and a status class
    _TW_LINK_PATTERN = re.compile(
        r'<a[^>]*href="(https://www\.ticketweb\.com/event/[^"]+)"[^>]*class="[^"]*tw_(\w+)"[^>]*>',
        re.DOTALL,
    )

    @staticmethod
    def extract_calendar_events(html: str) -> List[Dict]:
        """Parse the inline JS `var all_events` array from a calendar page.

        Returns a list of dicts with keys: title, start_date, url.
        """
        match = TicketWebExtractor._ALL_EVENTS_PATTERN.search(html)
        if not match:
            return []

        raw_array = match.group(1)
        events = []

        # Split on the object boundaries — each event is a { ... } block
        object_blocks = re.findall(r"\{(.*?)\}", raw_array, re.DOTALL)

        for block in object_blocks:
            title_match = TicketWebExtractor._TITLE_PATTERN.search(block)
            start_match = TicketWebExtractor._START_PATTERN.search(block)
            url_match = TicketWebExtractor._URL_PATTERN.search(block)

            if not (title_match and start_match and url_match):
                continue

            title = title_match.group(1).replace("\\'", "'")
            date_str = start_match.group(1)
            url = url_match.group(1).replace("\\'", "'")

            try:
                start_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                Logger.warn(
                    f"TicketWebExtractor: unparseable date '{date_str}' for '{title}'"
                )
                continue

            events.append({
                "title": title,
                "start_date": start_date,
                "url": url,
            })

        return events

    @staticmethod
    def extract_ticket_info(html: str) -> Tuple[Optional[str], bool]:
        """Extract the first TicketWeb ticket URL and sold-out status from a detail page.

        Returns (ticket_url, sold_out). The sold-out flag is derived from
        the CSS class on the buy button (tw_onsale vs tw_ticketssold).
        """
        # Try the specific buy button pattern first
        match = TicketWebExtractor._BUY_BUTTON_PATTERN.search(html)
        if not match:
            match = TicketWebExtractor._TW_LINK_PATTERN.search(html)

        if not match:
            return None, False

        ticket_url = match.group(1)
        status_class = match.group(2)
        sold_out = status_class == "ticketssold"

        return ticket_url, sold_out

    @staticmethod
    def build_events(
        calendar_events: List[Dict],
        ticket_info: Dict[str, Tuple[Optional[str], bool]],
    ) -> List[TicketWebEvent]:
        """Combine calendar event data with ticket info from detail pages.

        Args:
            calendar_events: Events from extract_calendar_events()
            ticket_info: Map of detail page URL → (ticket_url, sold_out)
        """
        events = []
        for ev in calendar_events:
            url = ev["url"]
            ticket_url, sold_out = ticket_info.get(url, (None, False))

            events.append(TicketWebEvent(
                name=ev["title"],
                start_date=ev["start_date"],
                show_page_url=url,
                ticket_url=ticket_url,
                sold_out=sold_out,
                performers=[ev["title"]],
            ))

        return events
