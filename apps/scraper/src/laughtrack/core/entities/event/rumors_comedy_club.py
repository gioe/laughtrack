"""Rumor's Comedy Club event model."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.foundation.utilities.html.utils import HtmlUtils
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class RumorsComedyClubEvent(ShowConvertible):
    """A single Rumor's Comedy Club performance."""

    name: str
    start_date: str
    show_page_url: str
    ticket_url: str
    ticket_price: Optional[float] = None
    ticket_type: str = "General Admission"
    description: str = ""
    ticket_options: List[Dict[str, object]] = field(default_factory=list)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        try:
            parsed_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                self.start_date, club.timezone or "America/Winnipeg"
            )
        except Exception:
            return None

        page_url = url or self.show_page_url
        ticket_url = self.ticket_url or page_url
        description = HtmlUtils.strip_tags(self.description).strip() if self.description else None
        raw_options = self.ticket_options or [
            {"purchase_url": ticket_url, "price": self.ticket_price, "type": self.ticket_type}
        ]
        tickets = [
            ShowFactoryUtils.create_fallback_ticket(
                str(option.get("purchase_url") or ticket_url),
                price=option.get("price") if isinstance(option.get("price"), (int, float)) else None,
                ticket_type=str(option.get("type") or "General Admission"),
            )
            for option in raw_options
        ]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=parsed_date,
            show_page_url=page_url,
            lineup=[],
            tickets=tickets,
            supplied_tags=["event"],
            description=description,
            enhanced=enhanced,
        )
