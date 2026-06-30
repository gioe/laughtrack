"""Data model for the Grisly Pear calendar listing."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.ports.scraping import EventListContainer
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class GrislyPearEvent(ShowConvertible):
    """A single event anchor from the Grisly Pear calendar listing."""

    name: str
    url: str
    date: str
    time: str

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        try:
            naive = datetime.strptime(f"{self.date} {self.time}", "%Y-%m-%d %H%M%S")
            start_date = naive.replace(tzinfo=ZoneInfo(club.timezone or "America/New_York"))
        except ValueError:
            return None

        show_url = url or self.url
        tickets = [ShowFactoryUtils.create_fallback_ticket(show_url)]
        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=start_date,
            show_page_url=show_url,
            lineup=[],
            tickets=tickets,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )


@dataclass
class GrislyPearPageData(EventListContainer[GrislyPearEvent]):
    """Container for extracted Grisly Pear events."""

    event_list: list[GrislyPearEvent]

