"""Data model for a single event scraped from the do314 / DoStuff Media API."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.utilities.datetime import DateTimeUtils
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

# Base host for the DoStuff Media city site. do314 (St. Louis) is one node of a
# larger network (do312 Chicago, do617 Boston, doLA, etc.) that all share the
# same `/venues/{slug}/events.json` JSON contract, so this scraper is reusable
# across the network by varying only the host stored in the source_url.
DO314_BASE_URL = "https://do314.com"


@dataclass
class Do314Event(ShowConvertible):
    """
    Data model for a single event fetched from the do314 / DoStuff Media API.

    Events are fetched per-venue via:
      GET https://do314.com/venues/<slug>/events.json

    The response groups events by day under ``event_groups[].events[]``. Each
    event carries a ``begin_time`` ISO 8601 string with a UTC offset, e.g.
    ``"2026-07-05T20:00:00-05:00"``, a relative ``permalink`` (the do314 event
    page), an optional ``buy_url`` (the ticketing link), and a
    ``category_param`` such as ``"comedy"`` or ``"music"`` used to isolate
    comedy programming at mixed-use venues.
    """

    event_id: str                       # do314 numeric event id (as string)
    title: str                          # Event title, e.g. "Apotheosis Comedy Showcase"
    begin_time: str                     # ISO 8601 with UTC offset, may be empty
    begin_date: str                     # Fallback date "YYYY-MM-DD" when begin_time is absent
    permalink: str                      # Relative do314 event page path, e.g. "/events/.../tickets"
    category_param: str                 # do314 category slug, e.g. "comedy"
    buy_url: Optional[str] = None       # Ticket purchase URL (may be empty)
    description: Optional[str] = None
    is_free: bool = False
    timezone_name: str = "America/Chicago"  # IANA tz used when begin_time lacks an offset
    artists: List[str] = field(default_factory=list)

    @property
    def show_page_url(self) -> str:
        """Absolute do314 event page URL (the venue's listing source)."""
        if self.permalink.startswith("http"):
            return self.permalink
        return f"{DO314_BASE_URL}{self.permalink}"

    def _resolve_date(self) -> Optional[datetime]:
        """Parse the event start into a timezone-aware datetime."""
        if self.begin_time:
            try:
                return datetime.fromisoformat(self.begin_time)
            except (ValueError, TypeError):
                pass
        if self.begin_date:
            try:
                return DateTimeUtils.parse_datetime_with_timezone(
                    self.begin_date, self.timezone_name
                )
            except (ValueError, TypeError):
                return None
        return None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a Do314Event to a Show domain object."""
        start_date = self._resolve_date()
        if start_date is None:
            return None

        page_url = url or self.show_page_url
        tickets = []
        ticket_url = self.buy_url or page_url
        if ticket_url:
            tickets.append(ShowFactoryUtils.create_fallback_ticket(ticket_url))

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=page_url,
            lineup=[],
            tickets=tickets,
            description=self.description or None,
            room=None,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
