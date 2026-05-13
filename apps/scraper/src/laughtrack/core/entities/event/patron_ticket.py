"""Data model for a single comedy event scraped via Salesforce PatronTicket.

Multiple comedy venues (The Lost Church, Reilly Arts Center, Marion Theatre, etc.)
host their ticketing on a shared Salesforce PatronTicket Visualforce Remoting stack
at ``<subdomain>.my.salesforce-sites.com/ticket``. The fetchEvents API returns events
with category tags, instance dates (epoch ms + pre-formatted strings), ticket URLs,
and sold-out status. The scraper filters to a configured category (default "Comedy")
at one or more Salesforce venue IDs supplied per-club via ``scraping_sources.metadata``.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class PatronTicketEvent(ShowConvertible):
    """A single comedy show instance on a Salesforce PatronTicket site.

    Fields map from the PatronTicket fetchEvents API response:
      event_name      ← event-level name (e.g. "The Setup - San Francisco")
      instance_name   ← instance-level name with date/time
      instance_id     ← Salesforce record ID for the instance
      epoch_ms        ← show start time as Unix epoch milliseconds (formattedDates.ISO8601)
      date_str        ← formatted date string from formattedDates.LONG_MONTH_DAY_YEAR
      time_str        ← formatted time string from formattedDates.TIME_STRING
      purchase_url    ← direct ticket purchase URL
      sold_out        ← whether the instance is sold out
      description     ← HTML detail field (may contain performer info)
      categories      ← semicolon-separated category tags from the event
      name_strip_suffixes ← optional list of trailing strings to strip from the show
                            name (per-venue config; the Lost Church names append a
                            " - San Francisco" suffix on the upstream side, for
                            example). Default empty.
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
    name_strip_suffixes: List[str] = field(default_factory=list)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        try:
            tz = ZoneInfo(club.timezone or "America/New_York")
            dt_utc = datetime.fromtimestamp(self.epoch_ms / 1000, tz=timezone.utc)
            start_date = dt_utc.astimezone(tz)
        except Exception:
            return None

        ticket_url = url or self.purchase_url
        tickets = [
            ShowFactoryUtils.create_fallback_ticket(
                ticket_url, sold_out=self.sold_out
            )
        ]

        name = self.event_name
        for suffix in self.name_strip_suffixes:
            if suffix and name.endswith(suffix):
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
