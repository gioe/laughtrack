"""Extract event data from TicketWeb-powered club calendar pages.

Phase 1: Parse the inline `var all_events = [...]` JS array from the calendar page
         to discover event names, dates, and detail page URLs.
         Fallback: parse the HTML-based ``tw-plugin-upcoming-event-list`` markup
         when the JS array is absent (some TicketWeb plugin configurations render
         events as server-side HTML instead of a client-side JS calendar).
Phase 2: Parse each event detail page to extract the TicketWeb ticket purchase URL
         and sold-out status.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from dateutil import parser as dateutil_parser

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

    # HTML-based event list patterns (server-rendered tw-plugin markup)
    _HTML_EVENT_NAME = re.compile(
        r'class="tw-name"[^>]*>\s*<a[^>]*>(.*?)</a>', re.DOTALL
    )
    _HTML_EVENT_DATE = re.compile(
        r'class="tw-event-date"[^>]*>(.*?)</span>', re.DOTALL
    )
    _HTML_EVENT_TIME = re.compile(
        r'class="tw-event-time"[^>]*>(.*?)</span>', re.DOTALL
    )
    _HTML_EVENT_LINK = re.compile(
        r'class="tw-name"[^>]*>\s*<a[^>]*href="([^"]+)"', re.DOTALL
    )

    # Pagination: next page link
    _NEXT_PAGE_PATTERN = re.compile(
        r'<a[^>]*class="[^"]*next[^"]*"[^>]*href="([^"]+)"', re.DOTALL
    )

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
    def extract_html_calendar_events(html: str) -> List[Dict]:
        """Parse the HTML-based ``tw-plugin-upcoming-event-list`` markup.

        Used as a fallback when ``var all_events`` is absent. Each event block
        contains ``tw-name``, ``tw-event-date``, ``tw-event-time`` elements.

        Returns a list of dicts with keys: title, start_date, url.
        """
        events: List[Dict] = []
        seen_urls: set = set()

        # Split HTML on "seven columns" blocks — each contains one event's metadata
        blocks = re.split(r'<div class="five columns">', html)

        for block in blocks[1:]:  # skip content before the first event
            name_match = TicketWebExtractor._HTML_EVENT_NAME.search(block)
            date_match = TicketWebExtractor._HTML_EVENT_DATE.search(block)
            time_match = TicketWebExtractor._HTML_EVENT_TIME.search(block)
            link_match = TicketWebExtractor._HTML_EVENT_LINK.search(block)

            if not (name_match and date_match and link_match):
                continue

            url = link_match.group(1).strip()
            if url in seen_urls:
                continue
            seen_urls.add(url)

            title = re.sub(r"<[^>]+>", "", name_match.group(1)).strip()

            # Parse date — format is typically "Apr 17 -" or "May 9 -"
            raw_date = re.sub(r"<[^>]+>", "", date_match.group(1)).strip()
            raw_date = raw_date.rstrip(" -")

            # Parse time — format is "Show: 9:00 PM" or "9:00 PM"
            raw_time = ""
            if time_match:
                raw_time = re.sub(r"<[^>]+>", "", time_match.group(1)).strip()
                raw_time = re.sub(r"^Show:\s*", "", raw_time).strip()

            date_str = f"{raw_date} {raw_time}".strip()

            try:
                start_date = dateutil_parser.parse(date_str)
                # dateutil defaults to the current year when no year is given.
                # If the resulting date is more than 30 days in the past, the
                # event likely belongs to next year (e.g., "Jan 10" parsed in
                # November should become next January).
                now = datetime.now()
                from datetime import timedelta

                if start_date < now - timedelta(days=30):
                    start_date = start_date.replace(year=now.year + 1)
            except (ValueError, TypeError):
                Logger.warn(
                    f"TicketWebExtractor: unparseable HTML date '{date_str}' for '{title}'"
                )
                continue

            events.append({
                "title": title,
                "start_date": start_date,
                "url": url,
            })

        return events

    @staticmethod
    def extract_next_page_url(html: str) -> Optional[str]:
        """Extract the next-page URL from pagination links, if present."""
        match = TicketWebExtractor._NEXT_PAGE_PATTERN.search(html)
        return match.group(1) if match else None

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
