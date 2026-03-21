"""Rodney's Comedy Club data extraction utilities."""

import re
from datetime import datetime
from typing import List, Optional

from laughtrack.core.entities.event.rodneys import RodneyEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper


class RodneyEventExtractor:
    """Utility class for extracting Rodney's Comedy Club event data from various sources."""

    @staticmethod
    def extract_show_links(html_content: str) -> List[str]:
        """
        Extract show page links from the main Rodney's page HTML.

        Args:
            html_content: HTML content from main page

        Returns:
            List of show page URLs
        """
        try:
            # Extract all links whose href starts with the shows path
            links = HtmlScraper.extract_links_by_text_pattern(
                html_content, "rodneysnewyorkcomedyclub.com/shows"
            )
            # Deduplicate while preserving order
            seen: set = set()
            show_links = []
            for link in links:
                if link not in seen:
                    seen.add(link)
                    show_links.append(link)
            return show_links
        except Exception as e:
            Logger.error(f"Failed to extract show links: {e}")
            return []

    @staticmethod
    def extract_events_from_html(html_content: str, source_url: str) -> List[RodneyEvent]:
        """
        Extract Rodney events from a show page.

        Tries JSON-LD first; falls back to direct HTML parsing when no
        structured data is present (current rodneysnewyorkcomedyclub.com behaviour).

        Args:
            html_content: HTML content from show page
            source_url: URL where the data was extracted from

        Returns:
            List of RodneyEvent objects
        """
        try:
            # Try JSON-LD first for forward compatibility
            events = EventExtractor.extract_events(html_content)
            if events:
                rodney_events = []
                for event in events:
                    try:
                        rodney_event = RodneyEvent.from_html_event(event, source_url)
                        rodney_events.append(rodney_event)
                    except Exception as e:
                        Logger.warn(f"Failed to convert Event to RodneyEvent: {e}")
                return rodney_events

            # Fall back to direct HTML parsing
            return RodneyEventExtractor._extract_event_from_html_page(html_content, source_url)

        except Exception as e:
            Logger.error(f"Failed to extract events from HTML: {e}")
            return []

    @staticmethod
    def _extract_event_from_html_page(html_content: str, source_url: str) -> List[RodneyEvent]:
        """
        Parse a show page's HTML directly to build a RodneyEvent.

        The current rodneysnewyorkcomedyclub.com show pages embed event data
        in specific CSS-classed elements rather than JSON-LD:
          - Title: <h4 class="uppercase ...">
          - Date:  <h4 class="mb-5 ..."> containing " | "
          - Ticket URL: first <a href="https://parde.app/...">

        Args:
            html_content: Raw HTML from a show page
            source_url: URL of the show page

        Returns:
            A one-element list with the parsed RodneyEvent, or [] on failure.
        """
        try:
            soup = HtmlScraper._parse_html(html_content)

            # Title — h4 with class "uppercase" (show title heading)
            title_tag = soup.find("h4", class_="uppercase")
            if not title_tag:
                Logger.warn(f"No title h4.uppercase found on {source_url}")
                return []
            title = title_tag.get_text(strip=True)
            if not title:
                return []

            # Date — h4 with class "mb-5" containing " | " separator
            date_time: Optional[datetime] = None
            for h4 in soup.find_all("h4", class_="mb-5"):
                text = h4.get_text(strip=True)
                if "|" in text:
                    date_time = RodneyEventExtractor._parse_show_date(text)
                    break

            if date_time is None:
                Logger.warn(f"Could not parse date on {source_url}")
                return []

            # Ticket URL (parde.app checkout link)
            ticket_url: Optional[str] = None
            for a in soup.find_all("a", href=True):
                if a["href"].startswith("https://parde.app"):
                    ticket_url = a["href"]
                    break

            event = RodneyEvent(
                id=RodneyEvent._generate_id_from_url(source_url),
                title=title,
                date_time=date_time,
                source_url=source_url,
                source_type="html",
                ticket_info={"purchase_url": ticket_url} if ticket_url else None,
            )
            return [event]

        except Exception as e:
            Logger.error(f"Failed to parse show page HTML from {source_url}: {e}")
            return []

    @staticmethod
    def _parse_show_date(date_str: str) -> Optional[datetime]:
        """
        Parse a date string from the show page into a naive datetime.

        Handles formats like:
          "Sat | March 21, 2026 - 8:30PM"
          "Sun | March 22, 2026 - 6 PM"
          "Mon | March 23, 2026 - 07:00PM"

        Args:
            date_str: Raw date string from the h4 element

        Returns:
            Naive datetime in the venue's local timezone (America/New_York).
            Timezone localization is applied downstream by the transformer.
            Returns None if parsing fails.
        """
        # Strip weekday prefix ("Sat | " etc.)
        m = re.search(r"\|\s*(.+)", date_str)
        if not m:
            return None
        rest = m.group(1).strip()

        # Match date and time parts: "March 21, 2026 - 8:30PM" / "- 6 PM"
        pattern = r"(\w+ \d+,\s*\d{4})\s*-\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM)"
        m = re.search(pattern, rest, re.IGNORECASE)
        if not m:
            return None

        date_part = m.group(1)
        hour = int(m.group(2))
        minute = int(m.group(3)) if m.group(3) else 0
        ampm = m.group(4).upper()

        if ampm == "PM" and hour != 12:
            hour += 12
        elif ampm == "AM" and hour == 12:
            hour = 0

        try:
            dt = datetime.strptime(date_part, "%B %d, %Y")
            return dt.replace(hour=hour, minute=minute)
        except ValueError:
            return None

    @staticmethod
    def extract_event_from_json_ld(html_content: str, source_url: str) -> Optional[RodneyEvent]:
        """
        Extract RodneyEvent from JSON-LD script tags in HTML.

        Args:
            html_content: HTML content containing JSON-LD script tags
            source_url: URL where the data was extracted from

        Returns:
            RodneyEvent object if successfully extracted, None otherwise
        """
        try:
            # Use the existing EventExtractor to get Event objects from JSON-LD
            events = EventExtractor.extract_events(html_content)

            if not events:
                Logger.warn(f"No events found in JSON-LD from {source_url}")
                return None

            # Convert the first Event to RodneyEvent
            event = events[0]  # Take the first event found
            rodney_event = RodneyEvent.from_html_event(event, source_url)
            return rodney_event

        except Exception as e:
            Logger.error(f"Failed to extract event from JSON-LD: {e}")
            return None
