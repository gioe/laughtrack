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
        lineup = ShowFactoryUtils.create_lineup_from_performers(self.performers)
        show = ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=self.start.astimezone(ZoneInfo(club.timezone)),
            show_page_url=self.ticket_url,
            tickets=[
                ShowFactoryUtils.create_fallback_ticket(self.ticket_url, price=self.price, sold_out=self.sold_out)
            ],
            lineup=lineup,
            enhanced=enhanced,
        )
        # The source names the performer explicitly. Substring matches in a
        # title (e.g. Andre De inside Andre De Freitas) must not add other acts.
        show.infer_lineup_from_title = not bool(lineup)
        return show


@dataclass
class ComedyConnectionPageData(EventListContainer[ComedyConnectionEvent]):
    event_list: List[ComedyConnectionEvent]
