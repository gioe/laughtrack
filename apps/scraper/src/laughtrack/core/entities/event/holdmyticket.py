"""Data model for a single show from a HoldMyTicket whitelabel site.

HoldMyTicket (holdmyticket.com, "hmt-front") is a ticketing platform whose
venues run branded whitelabel sites (``<venue>.holdmyticket.com``). The SPA
hydrates its event listing from a public JSON API keyed by the whitelabel
host::

    GET https://holdmyticket.com/api/public/events/nearby/api_key/anon
        /page/{n}/whitelabel/{host}
    -> {"events": [event, ...], "status": "ok", ...}

Each feed entry is the *head* of a repeating series (Fri/Sat runs) carrying a
``repeating_future_events`` count; the remaining showtimes come from::

    GET https://holdmyticket.com/api/public/events/repeating/id/{id}
        /whitelabel/{host}

``start``/``end`` are venue **wall-clock** strings (``2026-07-10 19:00:00``),
converted to an aware datetime with the club timezone here.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

_START_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class HoldMyTicketEvent(ShowConvertible):
    """A single comedy show fetched from a HoldMyTicket whitelabel feed.

    ``start_local`` is the venue wall-clock start (``%Y-%m-%d %H:%M:%S``).
    ``ticket_url`` is the per-showtime checkout page
    (``https://tickets.holdmyticket.com/tickets/{id}``), used as the access
    record for every show.
    """

    event_id: int
    title: str
    start_local: str                    # venue wall-clock, "%Y-%m-%d %H:%M:%S"
    ticket_url: str
    timezone_name: str = "America/Denver"

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a HoldMyTicketEvent to a Show domain object."""
        try:
            tz = ZoneInfo(club.timezone or self.timezone_name or "UTC")
            start_date = datetime.strptime(self.start_local, _START_FORMAT).replace(
                tzinfo=tz
            )
        except Exception:
            return None

        page_url = url or self.ticket_url
        tickets = []
        if page_url:
            tickets.append(ShowFactoryUtils.create_fallback_ticket(page_url))

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or "Comedy Show",
            club=club,
            date=start_date,
            show_page_url=page_url,
            lineup=[],
            tickets=tickets,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
