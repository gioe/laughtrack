"""Data model for a single comedy event at The Lost Church (San Francisco, CA).

The Lost Church uses Salesforce PatronTicket for ticketing. The API returns events
with category tags, instance dates (as epoch ms + formatted strings), ticket URLs,
and sold-out status. The scraper filters to events tagged "Comedy" at the SF venue.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.comedian.model import Comedian
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class LostChurchEvent(ShowConvertible):
    """A single comedy show instance at The Lost Church.

    Fields map from the PatronTicket fetchEvents API response:
      event_name      ← event-level name (e.g. "The Setup - San Francisco")
      instance_name   ← instance name with date/time (e.g. "Comedy: Stand-up | Friday, April 24th, 2026 | Doors 7:30pm")
      instance_id     ← Salesforce record ID for the instance
      epoch_ms        ← show start time as Unix epoch milliseconds (from formattedDates.ISO8601)
      date_str        ← formatted date string (e.g. "April 24, 2026") from formattedDates.LONG_MONTH_DAY_YEAR
      time_str        ← formatted time string (e.g. "7:30 PM") from formattedDates.TIME_STRING
      purchase_url    ← direct ticket purchase URL
      sold_out        ← whether the instance is sold out
      description     ← HTML detail field (may contain performer info)
      categories      ← semicolon-separated category tags from the event
    """

    event_name: str
    instance_name: str
    instance_id: str
    epoch_ms: int
    date_str: str
    time_str: str
    purchase_url: str
    sold_out: bool
    description: str
    categories: str

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert this PatronTicket instance to a Show domain object."""
        try:
            # Convert epoch ms to datetime in club timezone
            dt_utc = datetime.fromtimestamp(self.epoch_ms / 1000, tz=timezone.utc)
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                dt_utc.strftime("%Y-%m-%d %H:%M:%S"),
                club.timezone or "America/Los_Angeles",
            )
        except Exception:
            return None

        ticket_url = url or self.purchase_url
        tickets = [
            ShowFactoryUtils.create_fallback_ticket(
                ticket_url, sold_out=self.sold_out
            )
        ]

        # Use event name as the show name (strip city suffix)
        name = self.event_name
        for suffix in (" - San Francisco", " - SF", " - sf"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break

        return ShowFactoryUtils.create_enhanced_show_base(
            name=name,
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            description=None,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
