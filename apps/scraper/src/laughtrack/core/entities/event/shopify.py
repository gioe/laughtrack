"""Data model for a single event from a Shopify-based comedy venue.

Shopify stores expose product data at /collections/{handle}/products.json.
Each product represents a show, and each variant represents a specific
date/time + ticket tier.

Two product-title formats are supported:

  Format A (variant-date): Date/time is in the *variant* title:
    variant: "Thursday April 9 2026 / 8:00pm General Admission"
    product: "Michael Rapaport LIVE! [THU]"

  Format B (title-date): Date/time is in the *product* title:
    product: "Sat Apr 11th @6:30pm - Des Mulrooney, Caleb Synan and Landry"
    variant:  "General Admission" / "VIP"

The extractor tries Format A first; if no variant yields a date, it falls
back to Format B by calling ``_parse_product_title_datetime``.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


# ---------- Format A: date in variant title ----------
# Pattern: "Wednesday April 9 2026 / 8:00pm ..." or "Wednesday April 9 2026 / 8:00 PM ..."
_VARIANT_DATE_RE = re.compile(
    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
    r"(\w+ \d{1,2} \d{4})\s*/\s*(\d{1,2}:\d{2}\s*[APap][Mm])",
)

# ---------- Format B: date in product title ----------
# Pattern: "[prefix] <Day> <Mon> <DD>[th/st/nd/rd] @<H:MM>[am/pm] - <comedian(s)>"
# Examples:
#   "Sat Apr 11th @6:30pm - Des Mulrooney, Caleb Synan and Landry"
#   "*Late Show Pricing* Fri Apr 17th @9:30pm - Ross Bennett, JJ Whitehead and Brian Kiley"
_PRODUCT_TITLE_DATE_RE = re.compile(
    r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\w*\s+"         # day-of-week (abbreviated or full)
    r"(\w{3,9})\s+"                                    # month name (e.g. "Apr", "April")
    r"(\d{1,2})(?:st|nd|rd|th)?\s+"                    # day with optional ordinal
    r"@(\d{1,2}(?::\d{2})?\s*[APap][Mm])",             # time (e.g. "@6:30pm", "@7pm")
    re.IGNORECASE,
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

    Handles two formats:
      Format A: "Michael Rapaport LIVE! [THU]" → "Michael Rapaport"
      Format B: "Sat Apr 11th @6:30pm - Des Mulrooney, Caleb Synan and Landry"
               → "Des Mulrooney, Caleb Synan and Landry"
    """
    # Format B: if title contains " - " after a date pattern, extract comedian after separator
    if _PRODUCT_TITLE_DATE_RE.search(title):
        sep_idx = title.find(" - ")
        if sep_idx != -1:
            after = title[sep_idx + 3:].strip()
            if after:
                return after

    # Format A: strip suffixes
    cleaned = _TITLE_CLEANUP_RE.sub("", title).strip()
    return cleaned or title.strip()


def _parse_variant_datetime(variant_title: str, timezone: str) -> Optional[datetime]:
    """Parse a date/time from a Shopify variant title string (Format A).

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


def _parse_product_title_datetime(title: str, timezone: str) -> Optional[datetime]:
    """Parse a date/time from a Shopify product title string (Format B).

    Args:
        title: e.g. "Sat Apr 11th @6:30pm - Des Mulrooney, Caleb Synan and Landry"
        timezone: IANA timezone string

    Returns:
        A timezone-aware datetime, or None if parsing fails.
    """
    match = _PRODUCT_TITLE_DATE_RE.search(title)
    if not match:
        return None

    month_str = match.group(1)      # "Apr"
    day_str = match.group(2)        # "11"
    time_str = match.group(3).strip()  # "6:30pm"

    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(timezone)

        # Normalize time: insert colon if missing (e.g. "7pm" → "7:00 PM")
        time_normalized = re.sub(
            r"([ap]m)", lambda m: " " + m.group(1).upper(), time_str, flags=re.IGNORECASE
        ).strip()
        if ":" not in time_normalized.split()[0]:
            time_normalized = time_normalized.split()[0] + ":00 " + time_normalized.split()[1]

        # Infer year: use current year; if date is in the past, bump to next year
        now = datetime.now(tz)
        dt = datetime.strptime(f"{month_str} {day_str} {now.year} {time_normalized}", "%b %d %Y %I:%M %p")
        dt = dt.replace(tzinfo=tz)
        if dt < now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1):
            dt = dt.replace(year=now.year + 1)
        return dt
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
        # Use scraping_url base for ticket links (covers stores on a subdomain)
        base = (club.scraping_url or club.website or "").rstrip("/")
        base_clean = base.replace("https://", "").replace("http://", "").rstrip("/")
        ticket_url = url or f"https://{base_clean}/products/{self.handle}"
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
