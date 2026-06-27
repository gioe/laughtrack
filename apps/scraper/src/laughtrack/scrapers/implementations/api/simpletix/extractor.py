"""Extract event data from SimpleTix event pages.

SimpleTix embeds a JavaScript `var timeArray = [...]` on the event page with
individual show times. Each entry has an Id and Time string like:

    {"Id": 1330258, "Time": "Fri, Jan 2, 2026 7:30 PM - 9:00 PM"}

The page title and price info come from the HTML <h1> and JSON-LD respectively.
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from dateutil import parser as dateutil_parser

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger
from laughtrack.foundation.utilities.html.utils import HtmlUtils
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor


class SimpleTixExtractor:
    """Extracts event data from SimpleTix event pages."""

    _TIME_ARRAY_PATTERN = re.compile(
        r"var\s+timeArray\s*=\s*(\[.*?\]);", re.DOTALL
    )

    _TITLE_PATTERN = re.compile(r"<h1[^>]*>(.*?)</h1>", re.DOTALL)

    # Per-event SimpleTix permalinks, e.g. `/e/alex-kumin-...-tickets-273173`.
    # The numeric id after `-tickets-` is the stable key (the slug is truncated
    # in organizer-listing links but still resolves once fetched).
    _EVENT_LINK_PATTERN = re.compile(r"/e/[a-z0-9\-]+-tickets-(\d+)", re.IGNORECASE)

    @staticmethod
    def extract_listing_event_urls(html: str) -> List[str]:
        """Enumerate per-event SimpleTix URLs from an organizer/listing page.

        An organizer page (``{org}.simpletix.com/``) lists every show as a
        ``/e/{slug}-tickets-{id}`` link rather than embedding the showtimes
        directly. Returns absolute ``www.simpletix.com`` event-page URLs,
        de-duplicated by the numeric event id (the same event can appear under
        slightly different truncated slugs), preserving first-seen order.
        """
        seen_ids: set = set()
        urls: List[str] = []
        for match in SimpleTixExtractor._EVENT_LINK_PATTERN.finditer(html):
            event_id = match.group(1)
            if event_id in seen_ids:
                continue
            seen_ids.add(event_id)
            urls.append(f"https://www.simpletix.com{match.group(0)}")
        return urls

    @staticmethod
    def extract_jsonld_events(html: str) -> List[JsonLdEvent]:
        """Extract JSON-LD ``Event`` objects from a SimpleTix event page.

        Single-date SimpleTix events (one-off comedian bookings) render no
        ``var timeArray`` but still embed JSON-LD ``Event`` data with the
        startDate. This is the fallback source for those pages.
        """
        return EventExtractor.extract_events(html)

    @staticmethod
    def extract_time_array(html: str) -> List[Dict]:
        """Parse the inline JS `var timeArray` from the event page.

        Returns a list of dicts with keys: Id, Time.
        """
        match = SimpleTixExtractor._TIME_ARRAY_PATTERN.search(html)
        if not match:
            return []

        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError) as e:
            Logger.warn(f"SimpleTixExtractor: failed to parse timeArray: {e}")
            return []

    @staticmethod
    def extract_title(html: str) -> Optional[str]:
        """Extract the event title from the page <h1> tag."""
        match = SimpleTixExtractor._TITLE_PATTERN.search(html)
        if not match:
            return None
        title = HtmlUtils.strip_tags(match.group(1))
        # Strip common suffixes like " - Tickets"
        title = re.sub(r"\s*-\s*Tickets?\s*$", "", title, flags=re.IGNORECASE)
        return title or None

    @staticmethod
    def extract_json_ld_price(html: str) -> Optional[float]:
        """Lowest ticket price from the page's JSON-LD AggregateOffer.

        Delegates to the shared JSON-LD helper (convention 15), which handles
        single-object and top-level-array blocks, both offer shapes, and the
        AggregateOffer lowPrice fallback.
        """
        return EventExtractor.extract_min_offer_price(html)

    @staticmethod
    def parse_time_entry(time_str: str) -> Optional[datetime]:
        """Parse a SimpleTix time string like 'Fri, Jan 2, 2026 7:30 PM - 9:00 PM'.

        Only the start time portion (before the dash) is used.
        """
        # Split on " - " to get start time only
        start_part = time_str.split(" - ")[0].strip()

        try:
            return dateutil_parser.parse(start_part)
        except (ValueError, TypeError):
            Logger.warn(
                f"SimpleTixExtractor: unparseable time '{time_str}'"
            )
            return None

    @staticmethod
    def extract_events(
        html: str,
    ) -> Tuple[List[Dict], Optional[str], Optional[float]]:
        """Extract all event data from a SimpleTix page.

        Returns:
            (time_entries, title, price) where time_entries is the raw
            timeArray list, title is the event name, and price is the
            lowest ticket price from JSON-LD.
        """
        time_entries = SimpleTixExtractor.extract_time_array(html)
        title = SimpleTixExtractor.extract_title(html)
        price = SimpleTixExtractor.extract_json_ld_price(html)

        return time_entries, title, price
