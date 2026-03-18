"""
West Side Comedy Club event extractor.

West Side Comedy Club's website is built on the Punchup platform using Next.js App Router
with TanStack Query for data management. Show data is embedded in the page HTML as
React Query hydration state inside self.__next_f.push() streaming calls, NOT as JSON-LD.

This extractor parses those streaming calls to retrieve the venuePageCarousel query data.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.utilities.infrastructure.html.scraper import HtmlScraper


@dataclass
class WestSideShow:
    """A show parsed from the Punchup/West Side Comedy Club page hydration data."""

    id: str
    title: str
    datetime_str: str  # ISO 8601 local time: "2026-03-19T21:00:00"
    ticket_link: str
    tixologi_event_id: Optional[str]
    is_sold_out: bool
    metadata_text: Optional[str]
    show_comedians: List[Dict[str, Any]] = field(default_factory=list)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert to a Show entity."""
        try:
            date = ShowFactoryUtils.safe_parse_datetime_string(
                self.datetime_str,
                "%Y-%m-%dT%H:%M:%S",
                timezone_name="America/New_York",
            )
            if not date:
                Logger.warn(f"West Side: could not parse datetime '{self.datetime_str}' for show '{self.title}'")
                return None

            show_page_url = self.ticket_link or ""

            tickets: List[Ticket] = []
            if self.ticket_link:
                tickets.append(
                    ShowFactoryUtils.create_fallback_ticket(
                        purchase_url=self.ticket_link,
                        sold_out=self.is_sold_out,
                    )
                )

            # Build lineup from show_comedians sorted by ordering field
            sorted_comedians = sorted(
                self.show_comedians,
                key=lambda c: c.get("ordering", 0),
            )
            lineup = [
                Comedian(name=c["display_name"])
                for c in sorted_comedians
                if c.get("display_name")
            ]

            return ShowFactoryUtils.create_enhanced_show_base(
                name=self.title,
                club=club,
                date=date,
                show_page_url=show_page_url,
                lineup=lineup,
                tickets=tickets,
                description=self.metadata_text or None,
                room="",
                supplied_tags=["event"],
                enhanced=enhanced,
            )
        except Exception as e:
            Logger.error(f"West Side: failed to convert show '{self.title}': {e}")
            return None


class WestSideExtractor:
    """
    Extracts show data from West Side Comedy Club's Punchup-based Next.js page.

    The site embeds React Query state in self.__next_f.push([1, "..."]) streaming
    script tags. Each string value is a JSON-encoded chunk of the RSC payload that
    may contain the dehydrated TanStack Query cache, including the venuePageCarousel
    query with the full show list.
    """

    _CAROUSEL_KEY = "venuePageCarousel"
    _ITEMS_KEY = '"items":'

    @staticmethod
    def extract_shows(html_content: str) -> List[WestSideShow]:
        """
        Extract shows from the page HTML.

        Args:
            html_content: Raw HTML content of the calendar page.

        Returns:
            List of WestSideShow objects, empty list if none found.
        """
        if not html_content:
            return []

        try:
            script_elements = HtmlScraper.find_script_elements(html_content)
            for script in script_elements:
                content = script.get_text() if script else None
                if not content:
                    continue

                shows = WestSideExtractor._try_extract_from_script(content)
                if shows:
                    return shows

            return []
        except Exception as e:
            Logger.error(f"West Side: error extracting shows from HTML: {e}")
            return []

    @staticmethod
    def _try_extract_from_script(content: str) -> List[WestSideShow]:
        """
        Attempt to extract shows from a single script element's text content.

        Tries two strategies:
        1. Direct text search (for plain JSON embedded in the page).
        2. Decode JavaScript-escaped string from self.__next_f.push([1, "..."]) calls.
        """
        # Strategy 1: venuePageCarousel appears as plain text in this script
        if WestSideExtractor._CAROUSEL_KEY in content:
            shows = WestSideExtractor._extract_items_from_text(content)
            if shows:
                return shows

        # Strategy 2: content is a JS string — find push([1, "..."]) and decode
        for match in re.finditer(r'\[1,"((?:[^"\\]|\\.)*)"\]', content):
            try:
                decoded = json.loads('"' + match.group(1) + '"')
            except (json.JSONDecodeError, Exception):
                continue

            if WestSideExtractor._CAROUSEL_KEY not in decoded:
                continue

            shows = WestSideExtractor._extract_items_from_text(decoded)
            if shows:
                return shows

        return []

    @staticmethod
    def _extract_items_from_text(text: str) -> List[WestSideShow]:
        """
        Find the venuePageCarousel items array in decoded text and parse it.

        Locates the first occurrence of "venuePageCarousel" then finds the nearest
        "items": key, extracts the balanced JSON array, and parses it.
        """
        carousel_pos = text.find(WestSideExtractor._CAROUSEL_KEY)
        if carousel_pos == -1:
            return []

        items_key_pos = text.find(WestSideExtractor._ITEMS_KEY, carousel_pos)
        if items_key_pos == -1:
            return []

        array_start = text.find("[", items_key_pos + len(WestSideExtractor._ITEMS_KEY))
        if array_start == -1:
            return []

        array_json = WestSideExtractor._extract_balanced(text, array_start, "[", "]")
        if not array_json:
            return []

        try:
            items = json.loads(array_json)
        except json.JSONDecodeError as e:
            Logger.warn(f"West Side: failed to parse items JSON: {e}")
            return []

        return WestSideExtractor._parse_items(items)

    @staticmethod
    def _extract_balanced(text: str, start: int, open_ch: str, close_ch: str) -> Optional[str]:
        """
        Extract a balanced bracket/brace structure starting at position start.

        Skips characters inside JSON string values (double-quoted, with backslash-escape
        awareness) so that brackets or braces in string content do not affect the depth
        counter and produce a wrong or missing result.
        """
        depth = 0
        in_string = False
        i = start
        while i < len(text):
            ch = text[i]
            if in_string:
                if ch == "\\":
                    # Skip the escaped character — do not inspect it
                    i += 2
                    continue
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == open_ch:
                    depth += 1
                elif ch == close_ch:
                    depth -= 1
                    if depth == 0:
                        return text[start : i + 1]
            i += 1
        return None

    @staticmethod
    def _parse_items(items: list) -> List[WestSideShow]:
        """Convert raw carousel item dicts into WestSideShow objects."""
        shows = []
        for item in items:
            if not isinstance(item, dict) or item.get("type") != "show":
                continue

            show_data = item.get("show")
            if not isinstance(show_data, dict):
                continue

            title = show_data.get("title", "").strip()
            datetime_str = show_data.get("datetime", "").strip()

            if not title or not datetime_str:
                continue

            try:
                shows.append(
                    WestSideShow(
                        id=show_data.get("id", ""),
                        title=title,
                        datetime_str=datetime_str,
                        ticket_link=show_data.get("ticket_link", ""),
                        tixologi_event_id=show_data.get("tixologi_event_id"),
                        is_sold_out=bool(show_data.get("is_sold_out", False)),
                        metadata_text=show_data.get("metadata_text") or None,
                        show_comedians=show_data.get("show_comedians") or [],
                    )
                )
            except Exception as e:
                Logger.warn(f"West Side: skipping malformed show item: {e}")
                continue

        return shows
