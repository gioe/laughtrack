"""HTML extraction for the Laffs Comedy Cafe coming-soon page."""

import re
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup

from laughtrack.core.entities.event.laffs_comedy_cafe import LaffsComedyCafeEvent
from laughtrack.foundation.infrastructure.logger.logger import Logger

# The page URL doubles as the ticket URL since tickets are self-hosted.
_TICKET_URL = "https://www.laffstucson.com/coming-soon.html"

# Reservation form actions. The live page migrated make-res.php → make-res-v2.php
# (TASK-2483); accept both so a revert or A/B variant keeps working. The matching
# purchase form (action=tix2.php) carries identical showtimes, so we only ever
# read reservation forms to avoid double-counting events.
_RESERVATION_ACTIONS = frozenset({"make-res.php", "make-res-v2.php"})

# Pattern matching showtime radio labels like "Friday, April 10 @ 8 PM"
_SHOWTIME_RE = re.compile(
    r"^\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
    r",\s+\w+\s+\d{1,2}\s+@\s+\d{1,2}(?::\d{2})?\s*[AP]M\s*$",
    re.IGNORECASE,
)

# Seating radio labels look like "General - $15" / "Preferred - $20".
_SEATING_PRICE_RE = re.compile(r"\$\s*(\d+(?:\.\d{1,2})?)")

# Map the seating radio's value attribute to a stable ticket type. "general"
# keeps the historical "General Admission" type so existing rows update in place
# rather than orphaning a new tier alongside a stale $0 row.
_SEATING_TYPE_MAP = {
    "general": "General Admission",
    "preferred": "Preferred Seating",
}


class LaffsComedyCafeExtractor:
    """
    Parses the Laffs Comedy Cafe coming-soon page.

    The page at https://www.laffstucson.com/coming-soon.html renders each
    upcoming comedian with form elements containing ``data-name`` attributes
    (underscore-separated comedian names) and radio button labels for
    individual showtimes (e.g. "Friday, April 10 @ 8 PM").

    Each comedian has two forms (reservation + ticket purchase) with
    identical showtimes. We deduplicate by using only the reservation
    form (action in ``make-res.php`` / ``make-res-v2.php``) to avoid
    double-counting. The reservation form also renders the priced seating
    selector ("General - $15" / "Preferred - $20"), so per-tier prices are
    recovered from the same form.
    """

    @staticmethod
    def extract_events(html: str) -> List[LaffsComedyCafeEvent]:
        """Extract all show events from the coming-soon page."""
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        events: List[LaffsComedyCafeEvent] = []

        # Use forms with data-name to extract comedian + showtime pairs.
        # Only process reservation forms (not tix2.php purchase forms) to
        # avoid double-counting the identical showtimes.
        for form in soup.find_all("form", attrs={"data-name": True}):
            action = form.get("action", "")
            if action not in _RESERVATION_ACTIONS:
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

        seating_tiers = LaffsComedyCafeExtractor._parse_seating_tiers(form)

        events = []
        for showtime in showtimes:
            events.append(
                LaffsComedyCafeEvent(
                    comedian_name=comedian_name,
                    showtime_str=showtime,
                    ticket_url=_TICKET_URL,
                    seating_tiers=seating_tiers,
                )
            )

        return events

    @staticmethod
    def _parse_seating_tiers(form) -> List[Tuple[str, Optional[float]]]:
        """Extract priced seating tiers from the form's seating radios.

        The seating selector renders one radio per tier with a label like
        "General - $15" / "Preferred - $20". Returns a list of
        (ticket_type, price) tuples in document order, e.g.
        ``[("General Admission", 15.0), ("Preferred Seating", 20.0)]``.
        Returns ``[]`` when the form exposes no seating radios (older
        single-price layout), letting the caller fall back to one
        unpriced ticket.
        """
        tiers: List[Tuple[str, Optional[float]]] = []
        seen_types = set()

        for radio in form.find_all("input", attrs={"name": "showtimeSeating"}):
            value = (radio.get("value") or "").strip().lower()
            radio_id = radio.get("id")
            label = (
                form.find("label", attrs={"for": radio_id}) if radio_id else None
            )
            label_text = label.get_text(strip=True) if label else ""

            if not value and not label_text:
                continue

            match = _SEATING_PRICE_RE.search(label_text)
            price: Optional[float] = float(match.group(1)) if match else None

            ticket_type = _SEATING_TYPE_MAP.get(value)
            if ticket_type is None:
                # Unknown tier — derive a readable type from the label name
                # (the part before the price) or fall back to the raw value.
                name_part = label_text.split("-")[0].strip()
                ticket_type = name_part or value.title()

            if not ticket_type or ticket_type in seen_types:
                continue
            seen_types.add(ticket_type)
            tiers.append((ticket_type, price))

        return tiers
