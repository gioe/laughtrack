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

from laughtrack.foundation.infrastructure.logger.logger import Logger


class SimpleTixExtractor:
    """Extracts event data from SimpleTix event pages."""

    _TIME_ARRAY_PATTERN = re.compile(
        r"var\s+timeArray\s*=\s*(\[.*?\]);", re.DOTALL
    )

    _TITLE_PATTERN = re.compile(r"<h1[^>]*>(.*?)</h1>", re.DOTALL)

    _JSON_LD_PATTERN = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL,
    )

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
        title = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        # Strip common suffixes like " - Tickets"
        title = re.sub(r"\s*-\s*Tickets?\s*$", "", title, flags=re.IGNORECASE)
        return title or None

    @staticmethod
    def extract_json_ld_price(html: str) -> Optional[float]:
        """Extract the lowest ticket price from JSON-LD AggregateOffer."""
        match = SimpleTixExtractor._JSON_LD_PATTERN.search(html)
        if not match:
            return None

        try:
            ld = json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            return None

        offers = ld.get("offers")
        if not offers:
            return None

        # offers can be a single dict or a list
        if isinstance(offers, dict):
            offers = [offers]

        for offer in offers:
            low_price = offer.get("lowPrice")
            if low_price is not None:
                try:
                    return float(low_price)
                except (ValueError, TypeError):
                    continue

        return None

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
        html: str, scraping_url: str
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
