"""Data model for a single show from a Standing Room Only (SRO) venue.

Standing Room Only Tickets (standingroomonlytickets.com, "sromedia") is an
ASP.NET box-office platform. A venue's public events feed is served by a single
Kendo-UI endpoint::

    POST {base}/Event/ReadLiveEvents        (empty body -> all live events)
    -> {"Data": [ {"Id": 522, "EventTitle": "Kate Brindle",
                    "Shows": [ {"Start": "/Date(1783639800000)/",
                                "DisplayStartDayAndTime": "Thursday, July 9, 2026 at 7:30 PM",
                                "IsShowOld": false, ...}, ... ] }, ... ],
        "Total": 14, ...}

One feed entry is a *headliner residency* with one-or-more ``Shows`` (Thu/Fri/Sat
runs), so the extractor fans each event out to one StandingRoomOnlyEvent per
showtime. ``Start`` is a .NET ``/Date(ms)/`` epoch in **UTC** milliseconds — the
authoritative show datetime, converted to the club timezone here.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class StandingRoomOnlyEvent(ShowConvertible):
    """A single comedy show fetched from a Standing Room Only venue feed.

    ``start_ms`` is the .NET ``Start`` epoch in UTC milliseconds. ``show_page_url``
    is the SRO public event page (``{base}/WebOffice/EventList/{event_id}``),
    used as the access record for every show.
    """

    event_id: int
    title: str
    start_ms: int                       # .NET /Date(ms)/ epoch, UTC
    show_page_url: str
    timezone_name: str = "America/New_York"

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a StandingRoomOnlyEvent to a Show domain object."""
        try:
            tz = ZoneInfo(club.timezone or self.timezone_name or "UTC")
            start_date = datetime.fromtimestamp(
                self.start_ms / 1000, tz=timezone.utc
            ).astimezone(tz)
        except Exception:
            return None

        page_url = url or self.show_page_url
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
