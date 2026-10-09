"""One native calendar performance, preserving its actual ticket link."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.ports.scraping import EventListContainer
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class ComedyConnectionEvent(ShowConvertible):
    name: str
    start: datetime
    ticket_url: str
    sold_out: bool
    price: Optional[float] = None
    performers: List[str] = field(default_factory=list)

    def to_show(self, club, enhanced=True, url=None):
        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=self.start.astimezone(ZoneInfo(club.timezone)),
            show_page_url=self.ticket_url,
            tickets=[
                ShowFactoryUtils.create_fallback_ticket(self.ticket_url, price=self.price, sold_out=self.sold_out)
            ],
            lineup=ShowFactoryUtils.create_lineup_from_performers(self.performers),
            enhanced=enhanced,
        )


@dataclass
class ComedyConnectionPageData(EventListContainer[ComedyConnectionEvent]):
    event_list: List[ComedyConnectionEvent]
