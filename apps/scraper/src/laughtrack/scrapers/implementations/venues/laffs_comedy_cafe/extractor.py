"""HTML extraction for the Laffs Comedy Cafe coming-soon page."""

import re
from typing import List

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.laffs_comedy_cafe import LaffsComedyCafeEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# The page URL doubles as the ticket URL since tickets are self-hosted.
_TICKET_URL = "https://www.laffstucson.com/coming-soon.html"

# Pattern matching showtime radio labels like "Friday, April 10 @ 8 PM"
_SHOWTIME_RE = re.compile(
    r"^\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
    r",\s+\w+\s+\d{1,2}\s+@\s+\d{1,2}(?::\d{2})?\s*[AP]M\s*$",
    re.IGNORECASE,
)


class LaffsComedyCafeExtractor:
    """
    Parses the Laffs Comedy Cafe coming-soon page.

    The page at https://www.laffstucson.com/coming-soon.html renders each
    upcoming comedian with form elements containing ``data-name`` attributes
    (underscore-separated comedian names) and radio button labels for
    individual showtimes (e.g. "Friday, April 10 @ 8 PM").

    Each comedian has two forms (reservation + ticket purchase) with
    identical showtimes. We deduplicate by using only the reservation
    form (action=make-res.php) to avoid double-counting.
    """

    @staticmethod
    def extract_events(html: str) -> List[LaffsComedyCafeEvent]:
        """Extract all show events from the coming-soon page."""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[LaffsComedyCafeEvent] = []

        # Use forms with data-name to extract comedian + showtime pairs.
        # Only process reservation forms (make-res.php) to avoid duplicates.
        for form in soup.find_all("form", attrs={"data-name": True}):
            action = form.get("action", "")
            if action != "make-res.php":
                continue

            form_events = LaffsComedyCafeExtractor._parse_form(form)
            events.extend(form_events)

        return events

    @staticmethod
    def _parse_form(form) -> List[LaffsComedyCafeEvent]:
        """Parse a reservation form and return LaffsComedyCafeEvents."""
        data_name = form.get("data-name", "")
        if not data_name:
            return []

        # Convert underscore-separated name to proper name
        comedian_name = data_name.replace("_", " ").strip()
        if not comedian_name:
            Logger.debug("LaffsExtractor: skipping form — empty data-name")
            return []

        # Extract showtimes from radio button labels
        showtimes: List[str] = []
        for label in form.find_all("label"):
            text = label.get_text(strip=True)
            if _SHOWTIME_RE.match(text):
                showtimes.append(text)

        if not showtimes:
            Logger.debug(
                f"LaffsExtractor: no showtimes found for '{comedian_name}'"
            )
            return []

        events = []
        for showtime in showtimes:
            events.append(
                LaffsComedyCafeEvent(
                    comedian_name=comedian_name,
                    showtime_str=showtime,
                    ticket_url=_TICKET_URL,
                )
            )

        return events
