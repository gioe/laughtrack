from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class NicksEvent(ShowConvertible):
    """
    Data model representing a single event from Nick's Comedy Stop's Wix Events API.

    Ticket purchases are handled through Wix's native checkout; the event detail page
    URL (https://www.nickscomedystop.com/event-details/{slug}) serves as the ticket link.
    """

    id: str
    title: str
    description: str
    slug: str
    scheduling: Dict[str, Any]
    registration: Dict[str, Any]
    lineup: List[str] = field(default_factory=list)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        """Convert a NicksEvent to a Show."""
        scheduling_config = self.scheduling.get("config", {})
        date_str = scheduling_config.get("startDate")
        timezone = scheduling_config.get("timeZoneId", "America/New_York")

        start_date = None
        if date_str:
            start_date = ShowFactoryUtils.parse_wix_iso_date(date_str, timezone)

        if not start_date:
            return None

        base_url = "https://www.nickscomedystop.com"
        show_page_url = f"{base_url}/event-details/{self.slug}" if self.slug else ""

        # Extract ticket price from Wix native ticketing
        tickets = []
        ticketing = self.registration.get("ticketing", {})
        is_sold_out = bool(ticketing.get("soldOut", False))
        if ticketing and show_page_url:
            lowest = ticketing.get("lowestTicketPrice", {})
            amount = lowest.get("amount", "")
            if amount:
                try:
                    price = float(amount)
                    tickets.append(ShowFactoryUtils.create_fallback_ticket(show_page_url, price=price, sold_out=is_sold_out))
                except (ValueError, TypeError):
                    pass
        if not tickets and show_page_url:
            tickets.append(ShowFactoryUtils.create_fallback_ticket(show_page_url, sold_out=is_sold_out))

        name = self.title.strip() if self.title else "Comedy Show"

        return ShowFactoryUtils.create_enhanced_show_base(
            name=name,
            club=club,
            date=start_date,
            show_page_url=show_page_url,
            lineup=ShowFactoryUtils.create_lineup_from_performers(self.lineup),
            tickets=tickets,
            description=self.description if self.description else None,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
