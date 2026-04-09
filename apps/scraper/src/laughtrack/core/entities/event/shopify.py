"""Data model for a single event from a Shopify-based comedy venue.

Shopify stores expose product data at /collections/{handle}/products.json.
Each product represents a show, and each variant represents a specific
date/time + ticket tier. The variant title typically follows:

    "Thursday April 9 2026 / 8:00pm General Admission"

The comedian name is extracted from the product title by stripping common
suffixes like "LIVE!", day-of-week brackets, and trailing whitespace.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


# Pattern: "Wednesday April 9 2026 / 8:00pm ..." or "Wednesday April 9 2026 / 8:00 PM ..."
_VARIANT_DATE_RE = re.compile(
    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
    r"(\w+ \d{1,2} \d{4})\s*/\s*(\d{1,2}:\d{2}\s*[APap][Mm])",
)

# Suffixes to strip from product title to get comedian name
_TITLE_CLEANUP_RE = re.compile(
    r"\s*(?:LIVE!?|Live!?)\s*"       # "LIVE!" or "Live!"
    r"|\s*\[(?:MON|TUE|WED|THU|FRI|SAT|SUN)\]\s*"  # "[THU]" day markers
    r"|\s*\(.*?\)\s*",               # parenthetical notes
    flags=re.IGNORECASE,
)


def _extract_comedian_name(title: str) -> str:
    """Extract the comedian name from a Shopify product title.

    Examples:
        "Michael Rapaport LIVE! [THU]" → "Michael Rapaport"
        "The Shit Show LIVE! [THU]" → "The Shit Show"
        "LOLtino with Bryan Torresdey [THU]" → "LOLtino with Bryan Torresdey"
    """
    cleaned = _TITLE_CLEANUP_RE.sub("", title).strip()
    return cleaned or title.strip()


def _parse_variant_datetime(variant_title: str, timezone: str) -> Optional[datetime]:
    """Parse a date/time from a Shopify variant title string.

    Args:
        variant_title: e.g. "Thursday April 9 2026 / 8:00pm General Admission"
        timezone: IANA timezone string

    Returns:
        A timezone-aware datetime, or None if parsing fails.
    """
    match = _VARIANT_DATE_RE.match(variant_title)
    if not match:
        return None

    date_str = match.group(1)      # "April 9 2026"
    time_str = match.group(2).strip()  # "8:00pm"

    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(timezone)
        # Normalize time format: "8:00pm" → "8:00 PM"
        time_normalized = re.sub(r"([ap]m)", lambda m: " " + m.group(1).upper(), time_str, flags=re.IGNORECASE).strip()
        dt = datetime.strptime(f"{date_str} {time_normalized}", "%B %d %Y %I:%M %p")
        return dt.replace(tzinfo=tz)
    except Exception:
        return None


@dataclass
class ShopifyEvent(ShowConvertible):
    """A single show derived from a Shopify product + variant.

    Each Shopify product may have multiple variants (date/time combos).
    The extractor creates one ShopifyEvent per unique date/time, grouping
    ticket tiers as separate price points on the same show.
    """

    product_id: int
    title: str               # product title (e.g. "Michael Rapaport LIVE! [THU]")
    handle: str              # URL slug (e.g. "michael-rapaport-live-thu")
    show_date: datetime      # parsed from variant title
    price: str               # lowest price among variants for this date/time
    available: bool          # True if any variant for this date/time is available
    image_url: str = ""
    body_html: str = ""
    timezone: str = "America/Los_Angeles"
    tags: List[str] = field(default_factory=list)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a ShopifyEvent to a Show domain object."""
        comedian_name = _extract_comedian_name(self.title)
        ticket_url = url or f"https://{club.website.replace('https://', '').replace('http://', '').rstrip('/')}/products/{self.handle}"
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=comedian_name,
            club=club,
            date=self.show_date,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            description=None,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
