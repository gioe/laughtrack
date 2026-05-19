"""Event model for accesso ShoWare performance-list APIs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


@dataclass
class ShoWarePerformance(ShowConvertible):
    """Single performance row returned by ShoWare's performance list widget."""

    event_id: int
    performance_id: int
    title: str
    performance_name: str
    performance_datetime: str
    detail_url: str
    ticket_url: str
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sold_out: bool = False

    @classmethod
    def from_api_response(cls, item: dict, base_url: str) -> Optional["ShoWarePerformance"]:
        event_id = _int_or_none(item.get("EventID"))
        performance_id = _int_or_none(item.get("PerformanceID"))
        title = _clean(item.get("Event") or item.get("PerformanceName") or "")
        performance_datetime = _clean(item.get("PerformanceDateTime") or "")

        if not event_id or event_id < 0 or not performance_id or not title or not performance_datetime:
            return None

        base = base_url.rstrip("/")
        return cls(
            event_id=event_id,
            performance_id=performance_id,
            title=title,
            performance_name=_clean(item.get("PerformanceName") or ""),
            performance_datetime=performance_datetime,
            detail_url=f"{base}/eventperformances.asp?evt={event_id}",
            ticket_url=f"{base}/ordertickets.asp?p={performance_id}&src=default",
            min_price=_float_or_none(item.get("PerformanceMinPrice")),
            max_price=_float_or_none(item.get("PerformanceMaxPrice")),
            sold_out=_is_sold_out(item),
        )

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        try:
            naive = datetime.strptime(self.performance_datetime, "%A, %B %d, %Y %I:%M:%S %p")
        except ValueError:
            return None

        timezone_name = club.timezone or "America/New_York"
        show_date = naive.replace(tzinfo=ZoneInfo(timezone_name))
        ticket_url = url or self.ticket_url
        ticket_price = self.min_price if self.min_price is not None else 0.0
        tickets = [
            ShowFactoryUtils.create_fallback_ticket(
                ticket_url,
                price=ticket_price,
                sold_out=self.sold_out,
            )
        ]

        description_parts = []
        if self.performance_name and self.performance_name != self.title:
            description_parts.append(self.performance_name)
        if self.max_price is not None and self.max_price != self.min_price:
            description_parts.append(f"Price range: ${ticket_price:g}-${self.max_price:g}")

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=show_date,
            show_page_url=self.detail_url,
            lineup=[],
            tickets=tickets,
            description="; ".join(description_parts),
            supplied_tags=["event", "comedy"],
            enhanced=enhanced,
        )


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _int_or_none(value: object) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: object) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_sold_out(item: dict) -> bool:
    available = _int_or_none(item.get("AvailableTickets"))
    if available is not None and available <= 0:
        return True
    display_icon = str(item.get("DisplayIcon") or "").lower()
    return "sold" in display_icon
