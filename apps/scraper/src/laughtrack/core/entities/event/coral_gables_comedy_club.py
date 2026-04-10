"""Data model for a single event scraped from the Coral Gables Comedy Club website."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

_SITE_BASE = "https://www.saugatuckcomedy.com"


@dataclass
class CoralGablesComedyClubEvent(ShowConvertible):
    """
    Data model for a single event at Coral Gables Comedy Club (Saugatuck, MI).

    The venue uses Square Online (Weebly) for ticketing. Events are fetched from
    the public storefront products API with ``product_type=event``.

    Field mapping from Square Online API::

        name        ← product.name  (e.g. "Larry Reeb & Dan Turco")
        start_date  ← product.product_type_details.start_date  (e.g. "2026-04-11")
        start_time  ← product.product_type_details.start_time  (e.g. "8:00 PM")
        site_link   ← product.site_link  (e.g. "product/larry-reeb-dan-turco/18")
        price       ← product.price.regular  (cents)
        on_sale     ← product.on_sale
        sold_out    ← product.badges.out_of_stock
        performers  ← parsed from name by splitting on " & "
    """

    name: str
    start_date: str          # ISO date, e.g. "2026-04-11"
    start_time: str          # e.g. "8:00 PM"
    site_link: str           # relative URL path
    performers: List[str] = field(default_factory=list)
    price_cents: Optional[int] = None
    sold_out: bool = False

    def to_show(
        self, club: Club, enhanced: bool = True, url: Optional[str] = None
    ) -> Optional[Show]:
        """Convert this event to a Show domain object."""
        try:
            time_obj = datetime.strptime(self.start_time.strip(), "%I:%M %p")
            dt_str = f"{self.start_date} {time_obj.hour:02d}:{time_obj.minute:02d}:00"
            start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
                dt_str, club.timezone or "America/New_York"
            )
        except Exception:
            return None

        ticket_url = url or f"{_SITE_BASE}/{self.site_link}"

        price = (self.price_cents / 100.0) if self.price_cents else 0.0
        tickets = [
            ShowFactoryUtils.create_fallback_ticket(
                purchase_url=ticket_url,
                price=price,
                sold_out=self.sold_out,
            )
        ]

        lineup = ShowFactoryUtils.create_lineup_from_performers(self.performers)

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            lineup=lineup,
            tickets=tickets,
            description=None,
            room="Main Room",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
