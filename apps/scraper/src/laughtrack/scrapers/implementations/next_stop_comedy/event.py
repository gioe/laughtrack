from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class NextStopComedyEvent(ShowConvertible):
    title: str
    start_date: datetime
    event_url: str
    venue_name: str
    venue_address: str = ""
    venue_zip: str = ""
    venue_timezone: Optional[str] = None
    description: Optional[str] = None
    performers: list[Any] = field(default_factory=list)
    ticket_price: Optional[float] = None
    sold_out: bool = False

    def venue_payload(self) -> dict:
        return {
            "name": self.venue_name,
            "address": self.venue_address,
            "zip_code": self.venue_zip,
            "timezone": self.venue_timezone,
        }

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        source_url = url or self.event_url
        lineup = ShowFactoryUtils.create_lineup_from_performers(self.performers)
        tickets = [
            ShowFactoryUtils.create_fallback_ticket(
                source_url,
                price=self.ticket_price,
                sold_out=self.sold_out,
            )
        ]
        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title or club.name,
            club=club,
            date=self.start_date,
            show_page_url=source_url,
            lineup=lineup,
            tickets=tickets,
            description=self.description,
            supplied_tags=["event"],
            enhanced=enhanced,
        )
