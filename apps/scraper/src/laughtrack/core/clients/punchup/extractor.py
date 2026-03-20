"""
Punchup platform extractor.

Punchup is a comedy venue booking platform built on Next.js App Router with
TanStack Query. Show data is embedded in the page HTML as React Query hydration
state inside self.__next_f.push() streaming calls, NOT as JSON-LD.

Venues using Punchup include:
- West Side Comedy Club (westsidecomedyclub.com)
- Comedy Key West (comedykeywest.com)

This extractor parses those streaming calls to retrieve the venuePageCarousel
query data, which contains the full event listing with lineup and ticket info.
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
class PunchupShow:
    """A show parsed from a Punchup platform page hydration data."""

    id: str
    title: str
    datetime_str: str  # ISO 8601 local time: "2026-03-19T21:00:00"
    ticket_link: str
    tixologi_event_id: Optional[str]
    is_sold_out: bool
    metadata_text: Optional[str]
    show_comedians: List[Dict[str, Any]] = field(default_factory=list)

    def to_show(
        self,
        club: Club,
        enhanced: bool = True,
        url: Optional[str] = None,
    ) -> Optional[Show]:
        """Convert to a Show entity."""
        try:
            date = ShowFactoryUtils.safe_parse_datetime_string(
                self.datetime_str,
                "%Y-%m-%dT%H:%M:%S",
                timezone_name=club.timezone or "America/New_York",
            )
            if not date:
                Logger.warn(
                    f"Punchup ({club.name}): could not parse datetime '{self.datetime_str}' for show '{self.title}'"
                )
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
            Logger.error(f"Punchup ({club.name}): failed to convert show '{self.title}': {e}")
            return None


class PunchupExtractor:
    """
    Extracts show data from a Punchup platform Next.js page.

    The site embeds React Query state in self.__next_f.push([1, "..."]) streaming
    script tags. Each string value is a JSON-encoded chunk of the RSC payload that
    may contain the dehydrated TanStack Query cache, including the venuePageCarousel
    query with the full show list.

    This extractor is platform-generic and works for any Punchup venue.
    """

    _CAROUSEL_KEY = "venuePageCarousel"
    _ITEMS_KEY = '"items":'
    _VENUE_SHOWS_KEY = "venueShows"

    @staticmethod
    def extract_shows(html_content: str) -> List[PunchupShow]:
        """
        Extract shows from the page HTML.

        Args:
            html_content: Raw HTML content of the venue calendar page.

        Returns:
            List of PunchupShow objects, empty list if none found.
        """
        if not html_content:
            return []

        try:
            script_elements = HtmlScraper.find_script_elements(html_content)
            for script in script_elements:
                content = script.get_text() if script else None
                if not content:
                    continue

                shows = PunchupExtractor._try_extract_from_script(content)
                if shows:
                    return shows

            return []
        except Exception as e:
            Logger.error(f"Punchup: error extracting shows from HTML: {e}")
            return []

    @staticmethod
    def _try_extract_from_script(content: str) -> List[PunchupShow]:
        """
        Attempt to extract shows from a single script element's text content.

        Tries two strategies:
        1. Direct text search (for plain JSON embedded in the page).
           Only the venuePageCarousel path is checked here — venueShows data is always
           inside a push([1, "..."]) call in practice and is handled in Strategy 2.
        2. Decode JavaScript-escaped string from self.__next_f.push([1, "..."]) calls.
        """
        # Strategy 1: venuePageCarousel appears as plain text in this script
        if PunchupExtractor._CAROUSEL_KEY in content:
            shows = PunchupExtractor._extract_items_from_text(content)
            if shows:
                return shows

        # Strategy 2: content is a JS string — find push([1, "..."]) and decode
        for match in re.finditer(r'\[1,"((?:[^"\\]|\\.)*)"\]', content):
            try:
                decoded = json.loads('"' + match.group(1) + '"')
            except (json.JSONDecodeError, Exception):
                continue

            if PunchupExtractor._CAROUSEL_KEY in decoded:
                shows = PunchupExtractor._extract_items_from_text(decoded)
                if shows:
                    return shows

            if PunchupExtractor._VENUE_SHOWS_KEY in decoded:
                shows = PunchupExtractor._extract_venue_shows_from_text(decoded)
                if shows:
                    return shows

        return []

    @staticmethod
    def _extract_items_from_text(text: str) -> List[PunchupShow]:
        """
        Find the venuePageCarousel items array in decoded text and parse it.

        Locates the "venuePageCarousel" anchor then finds the nearest "items": key.
        Falls back to searching from the beginning of the text when the items array
        precedes the carousel key (e.g. it lives in the "venue-page-theme" query).
        Extracts the balanced JSON array and parses it.
        """
        carousel_pos = text.find(PunchupExtractor._CAROUSEL_KEY)
        if carousel_pos == -1:
            return []

        items_key_pos = text.find(PunchupExtractor._ITEMS_KEY, carousel_pos)
        if items_key_pos == -1:
            # The items array may appear before venuePageCarousel (e.g. in venue-page-theme).
            # Anchor the backward search to the last '"queryKey"' before the carousel key
            # to avoid matching an unrelated query's "items": from earlier in the payload.
            anchor = text.rfind('"queryKey"', 0, carousel_pos)
            search_from = max(0, anchor) if anchor != -1 else 0
            items_key_pos = text.find(PunchupExtractor._ITEMS_KEY, search_from)
        if items_key_pos == -1:
            return []

        array_start = text.find("[", items_key_pos + len(PunchupExtractor._ITEMS_KEY))
        if array_start == -1:
            return []

        array_json = PunchupExtractor._extract_balanced(text, array_start, "[", "]")
        if not array_json:
            return []

        try:
            items = json.loads(array_json)
        except json.JSONDecodeError as e:
            Logger.warn(f"Punchup: failed to parse items JSON: {e}")
            return []

        return PunchupExtractor._parse_items(items)

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
    def _parse_items(items: list) -> List[PunchupShow]:
        """Convert raw carousel item dicts into PunchupShow objects."""
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
                    PunchupShow(
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
                Logger.warn(f"Punchup: skipping malformed show item: {e}")
                continue

        return shows

    @staticmethod
    def _extract_venue_shows_from_text(text: str) -> List[PunchupShow]:
        """
        Extract shows from a venueShows React Query state in decoded text.

        The venueShows query uses a flat show format: data is a direct array of show
        objects (not wrapped in {"type":"show","show":{...}}). The queryKey appears
        AFTER the state data, so we search backward from the key to find "data":[.
        """
        key_pos = text.find('"queryKey":["' + PunchupExtractor._VENUE_SHOWS_KEY)
        if key_pos == -1:
            return []

        # Search backward from the queryKey for the venueShows state's "data":[ array.
        # Use the more specific '"state":{"data":[' to avoid matching "data":[ from an
        # unrelated earlier React Query entry in the same payload.
        state_data_key = '"state":{"data":['
        state_pos = text.rfind(state_data_key, 0, key_pos)
        if state_pos == -1:
            # Fall back to bare "data":[ if the state block uses a different layout
            data_key = '"data":['
            state_pos = text.rfind(data_key, 0, key_pos)
            if state_pos == -1:
                return []
            array_start = state_pos + len(data_key) - 1
        else:
            array_start = state_pos + len(state_data_key) - 1  # points at the '['
        array_json = PunchupExtractor._extract_balanced(text, array_start, "[", "]")
        if not array_json:
            return []

        try:
            items = json.loads(array_json)
        except json.JSONDecodeError as e:
            Logger.warn(f"Punchup (venueShows): failed to parse shows JSON: {e}")
            return []

        return PunchupExtractor._parse_venue_shows_items(items)

    @staticmethod
    def _parse_venue_shows_items(items: list) -> List[PunchupShow]:
        """Convert flat venueShows array items into PunchupShow objects."""
        shows = []
        for item in items:
            if not isinstance(item, dict):
                continue

            title = (item.get("title") or "").strip()
            datetime_str = (item.get("datetime") or "").strip()

            if not title or not datetime_str:
                continue

            try:
                shows.append(
                    PunchupShow(
                        id=item.get("id", ""),
                        title=title,
                        datetime_str=datetime_str,
                        ticket_link=item.get("ticket_link", ""),
                        tixologi_event_id=item.get("tixologi_event_id"),
                        is_sold_out=bool(item.get("is_sold_out", False)),
                        metadata_text=item.get("metadata_text") or None,
                        show_comedians=item.get("show_comedians") or [],
                    )
                )
            except Exception as e:
                Logger.warn(f"Punchup (venueShows): skipping malformed show item: {e}")
                continue

        return shows
