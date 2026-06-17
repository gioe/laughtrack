"""Data model for UCB WP Grid Builder show cards."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class UCBEvent(ShowConvertible):
    """One dated UCB show card from the WP Grid Builder listing."""

    title: str
    date_text: str
    show_page_url: str
    ticket_url: str
    location_slug: str
    location_name: str
    description: str = ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        try:
            parsed = datetime.strptime(self.date_text.strip(), "%A, %B %d, %Y @ %I:%M %p")
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                parsed.strftime("%Y-%m-%d %H:%M:%S"),
                club.timezone or "America/Los_Angeles",
            )
        except Exception:
            return None

        ticket_url = url or self.ticket_url or self.show_page_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_date,
            show_page_url=self.show_page_url or ticket_url,
            description=self.description,
            room=self.location_name,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
