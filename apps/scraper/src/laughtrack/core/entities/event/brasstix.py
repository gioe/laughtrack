"""Event model for BrassTix inline calendar entries."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class BrassTixEvent(ShowConvertible):
    """Single event object embedded in a BrassTix calendar page."""

    event_id: str
    title: str
    start: str
    ticket_url: str
    show_name: str
    availability_label: str = ""
    price: Optional[float] = None

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        try:
            naive = datetime.strptime(self.start, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

        timezone_name = club.timezone or "America/New_York"
        show_date = naive.replace(tzinfo=ZoneInfo(timezone_name))
        purchase_url = url or self.ticket_url
        tickets = [
            ShowFactoryUtils.create_fallback_ticket(
                purchase_url,
                price=self.price,
                sold_out=False,
            )
        ]
        description = self.availability_label if self.availability_label else ""

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=show_date,
            show_page_url=purchase_url,
            lineup=[],
            tickets=tickets,
            description=description,
            supplied_tags=["event", "comedy"],
            enhanced=enhanced,
        )
