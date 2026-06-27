"""Data model for a single event scraped from Coral Springs Center for the Arts."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class CoralSpringsCenterEvent(ShowConvertible):
    """A single comedy event at Coral Springs Center for the Arts (Coral Springs, FL).

    The venue is a multi-genre performing-arts theater whose own site
    (thecentercs.com) exposes a server-rendered, category-filtered comedy
    listing at ``/events/category/comedy``. Each event's own detail page
    (``/events/detail/<slug>``) is the source of truth for the title, full date
    (``m-date__month`` / ``m-date__day`` / ``m-date__year`` spans) and showtime;
    ticketing links out to the venue's eVenue box office (which is bot-walled, so
    ``show_page_url`` points at the venue's own detail page).
    """

    name: str
    start_date: str          # ISO date, e.g. "2026-10-09"
    start_time: str          # e.g. "7:30PM"
    detail_url: str          # the venue's own /events/detail/<slug> page
    ticket_url: Optional[str] = None  # eVenue SEGetEventInfo buy link

    def to_show(
        self, club: Club, enhanced: bool = True, url: Optional[str] = None
    ) -> Optional[Show]:
        """Convert this event to a Show domain object."""
        try:
            time_obj = datetime.strptime(self.start_time.strip().upper(), "%I:%M%p")
            dt_str = f"{self.start_date} {time_obj.hour:02d}:{time_obj.minute:02d}:00"
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                dt_str, club.timezone or "America/New_York"
            )
        except Exception:
            return None

        page_url = url or self.detail_url
        tickets = [
            ShowFactoryUtils.create_fallback_ticket(
                purchase_url=self.ticket_url or page_url,
            )
        ]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=start_date,
            show_page_url=page_url,
            tickets=tickets,
            supplied_tags=["comedy"],
            enhanced=enhanced,
        )
