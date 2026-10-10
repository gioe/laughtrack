"""Verified native Stir Crazy performances."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.ports.scraping import EventListContainer
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class StirCrazyEvent(ShowConvertible):
    name: str
    start: datetime
    ticket_url: str
    sold_out: bool
    price: Optional[float]
    performers: List[str] = field(default_factory=list)
    ticket_options: List[dict] = field(default_factory=list)

    def to_show(self, club, enhanced=True, url=None):
        show = ShowFactoryUtils.create_enhanced_show_base(
            name=self.name, club=club, date=self.start, show_page_url=self.ticket_url,
            tickets=[ShowFactoryUtils.create_fallback_ticket(self.ticket_url, **option)
                     for option in self.ticket_options] if self.ticket_options else [
                         ShowFactoryUtils.create_fallback_ticket(self.ticket_url, price=self.price, sold_out=self.sold_out)],
            lineup=ShowFactoryUtils.create_lineup_from_performers(self.performers),
            enhanced=enhanced,
        )
        # The source emits fake Person objects for show titles too. Unknown
        # lineups must stay unknown rather than gaining substring title matches.
        show.infer_lineup_from_title = False
        return show


@dataclass
class StirCrazyPageData(EventListContainer[StirCrazyEvent]):
    event_list: List[StirCrazyEvent]
