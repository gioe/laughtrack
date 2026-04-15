"""
Off Cabot Comedy and Events data extraction utilities.

Two-phase extraction:
1. Listing page (/offcabot/) — parse event_item cards to discover event page URLs.
2. Event detail pages (/event/<slug>/) — parse show_row entries for date, time,
   price, and ticket URL (Etix or native booking).
"""

import re
from typing import List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from laughtrack.core.entities.event.off_cabot import OffCabotEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger


class OffCabotExtractor:
    """Pure parsing utilities for Off Cabot listing and detail pages."""

    @staticmethod
    def extract_event_page_urls(html: str, base_url: str) -> List[str]:
        """
        Extract event page URLs from the Off Cabot listing page.

        Parses div.event_item cards and returns unique /event/<slug>/ URLs.
        """
        urls: List[str] = []
        seen: set = set()
        try:
            soup = BeautifulSoup(html, "html.parser")
            items = soup.find_all("div", class_="event_item")

            for item in items:
                url = OffCabotExtractor._extract_event_url(item, base_url)
                if url and url not in seen:
                    seen.add(url)
                    urls.append(url)

        except Exception as e:
            Logger.error(f"OffCabotExtractor: Failed to extract event URLs: {e}")

        return urls

    @staticmethod
    def _extract_event_url(item: Tag, base_url: str) -> Optional[str]:
        """Extract the event page URL from an event_item card."""
        # The "Buy Tickets" link in div.event_btn
        btn_div = item.find("div", class_="event_btn")
        if btn_div:
            link = btn_div.find("a", href=True)
            if link:
                href = link["href"]
                if "/event/" in href:
                    return urljoin(base_url, href)

        # Fallback: thumbnail link
        thumb_link = item.find("div", class_="event_thumb")
        if thumb_link:
            link = thumb_link.find("a", href=True)
            if link and "/event/" in link["href"]:
                return urljoin(base_url, link["href"])

        return None

    @staticmethod
    def extract_events_from_detail(html: str, event_page_url: str) -> List[OffCabotEvent]:
        """
        Extract events from an Off Cabot event detail page.

        Each show_row in the show_details_table becomes a separate event.
        Multi-date events produce multiple OffCabotEvent objects.
        """
        events: List[OffCabotEvent] = []
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Get event name from h1 or p.h2
            name = OffCabotExtractor._extract_name(soup)
            if not name:
                Logger.debug(f"OffCabotExtractor: No event name found on {event_page_url}")
                return []

            # Parse each show_row in the ticket table
            table = soup.find("div", class_="show_details_table")
            if not table:
                Logger.debug(f"OffCabotExtractor: No show_details_table on {event_page_url}")
                return []

            rows = table.find_all("div", class_="show_row")
            for row in rows:
                event = OffCabotExtractor._parse_show_row(row, name, event_page_url)
                if event:
                    events.append(event)

        except Exception as e:
            Logger.error(f"OffCabotExtractor: Failed to extract from {event_page_url}: {e}")

        return events

    @staticmethod
    def _extract_name(soup: BeautifulSoup) -> Optional[str]:
        """Extract the event name from the detail page."""
        # The name is in a p.h2 that's NOT inside the show_times (Buy Tickets) section
        show_times = soup.find("div", class_="show_times")
        for p in soup.find_all("p", class_="h2"):
            if show_times and show_times.find(lambda t: t is p):
                continue
            text = p.get_text(strip=True)
            if text:
                return text

        # Fallback: page <title> stripped of " | The Cabot"
        title_tag = soup.find("title")
        if title_tag:
            text = title_tag.get_text(strip=True)
            if " | " in text:
                text = text.split(" | ")[0].strip()
            if text:
                return text

        return None

    @staticmethod
    def _parse_show_row(row: Tag, name: str, event_page_url: str) -> Optional[OffCabotEvent]:
        """Parse a single show_row into an OffCabotEvent."""
        try:
            cols = row.find_all("div", class_="show_col")
            if len(cols) < 3:
                return None

            # Column order: date, time, price, book button
            date_text = cols[0].get_text(strip=True)
            time_text = cols[1].get_text(strip=True)
            price_text = cols[2].get_text(strip=True)

            # Ticket URL from the "Book Now" link
            ticket_url = event_page_url
            book_link = row.find("a", class_="btn", href=True)
            if book_link:
                ticket_url = book_link["href"]

            if not date_text:
                return None

            return OffCabotEvent(
                name=name,
                date_text=date_text,
                time_text=time_text,
                price_text=price_text,
                ticket_url=ticket_url,
                event_page_url=event_page_url,
            )
        except Exception as e:
            Logger.error(f"OffCabotExtractor: Failed to parse show_row: {e}")
            return None
