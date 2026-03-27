"""Data model for a single event from a Squarespace-powered venue."""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

_HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class SquarespaceEvent(ShowConvertible):
    """
    Data model for a single event from a Squarespace-hosted venue's API.

    The API endpoint pattern is:
      GET {domain}/api/open/GetItemsByMonth?month=MM-YYYY&collectionId={id}

    The response is a JSON array at the root level. Fields map from:
      id           ← event["id"]
      title        ← event["title"]
      start_date_ms ← event["startDate"] (Unix milliseconds)
      full_url     ← event["fullUrl"] (relative path, e.g. "/calendar/2026/4/3/...")
      base_domain  ← extracted from club.scraping_url at scrape time
      excerpt      ← event["excerpt"] (HTML string, stripped for description)

    Note: ticketingUrl is not present in the bulk GetItemsByMonth response.
    The show_page_url (base_domain + full_url) serves as the ticket fallback.
    """

    id: str
    title: str
    start_date_ms: int     # Unix timestamp in milliseconds
    full_url: str          # Relative path, e.g. "/calendar/2026/4/3/..."
    base_domain: str       # e.g. "https://thedentheatre.com"
    excerpt: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a SquarespaceEvent to a Show domain object."""
        try:
            tz = ZoneInfo(club.timezone or "UTC")
            start_date = datetime.fromtimestamp(
                self.start_date_ms / 1000, tz=timezone.utc
            ).astimezone(tz)
        except Exception:
            return None

        show_page_url = url or (self.base_domain.rstrip("/") + self.full_url)

        description = _HTML_TAG_RE.sub("", self.excerpt).strip() or None

        tickets = [ShowFactoryUtils.create_fallback_ticket(show_page_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            description=description,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
