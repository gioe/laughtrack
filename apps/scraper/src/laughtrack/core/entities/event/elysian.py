"""Data model for a single event from The Elysian Theater's Squarespace API."""

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
class ElysianEvent(ShowConvertible):
    """
    Data model for a single event from The Elysian Theater's Squarespace API.

    The API endpoint is:
      https://www.elysiantheater.com/api/open/GetItemsByMonth

    Fields map directly from the API response.
    """

    id: str
    title: str
    start_date_ms: int  # Unix timestamp in milliseconds
    full_url: str  # Relative path, e.g. "/shows/spots0331"
    excerpt: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert an ElysianEvent to a Show domain object."""
        try:
            tz = ZoneInfo(club.timezone or "America/Los_Angeles")
            start_date = datetime.fromtimestamp(
                self.start_date_ms / 1000, tz=timezone.utc
            ).astimezone(tz)
        except Exception:
            return None

        show_page_url = url or ("https://www.elysiantheater.com" + self.full_url)

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
