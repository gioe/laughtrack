"""
Data model for a single performance from Post Office Cafe & Cabaret.

Show data is fetched from the ThunderTix calendar API at:
  https://postofficecafecabaret.thundertix.com/reports/calendar?week=0&start={ts}&end={ts+7d}

Each item in the JSON array represents a single performance with title, start
datetime (with UTC offset), event/performance IDs, and ticket/show page URLs.
"""

from dataclasses import dataclass
from datetime import datetime

from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.core.entities.club.model import Club

from typing import Optional


@dataclass
class PostOfficeCafePerformance(ShowConvertible):
    """
    Data model representing a single performance from Post Office Cafe & Cabaret.

    Fields map directly to the JSON objects returned by the ThunderTix
    calendar API endpoint.
    """

    event_id: int
    performance_id: int
    title: str
    start_dt: str       # raw datetime string, e.g. "2026-04-11 11:00:00 -0500"
    ticket_url: str     # full URL: base_url + order_products_url
    show_page_url: str  # full URL: base_url + truncated_url
    is_sold_out: bool = False

    @classmethod
    def from_api_response(cls, data: dict, base_url: str) -> "PostOfficeCafePerformance":
        """Create a PostOfficeCafePerformance from a raw ThunderTix API dict."""
        order_products_url = data.get("order_products_url") or ""
        truncated_url = data.get("truncated_url") or ""
        return cls(
            event_id=int(data.get("event_id", 0)),
            performance_id=int(data.get("performance_id", 0)),
            title=data.get("title") or "",
            start_dt=data.get("start") or "",
            ticket_url=f"{base_url}{order_products_url}",
            show_page_url=f"{base_url}{truncated_url}",
            is_sold_out=bool(data.get("is_sold_out", False)),
        )

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show object."""
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.title or not self.start_dt:
            return None

        try:
            start_date = datetime.strptime(self.start_dt, "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            return None

        ticket_url = url or self.ticket_url
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url, sold_out=self.is_sold_out)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_date,
            show_page_url=self.show_page_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
