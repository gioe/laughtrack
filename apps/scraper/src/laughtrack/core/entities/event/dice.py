"""Data model for events returned by the DICE partner event-list API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible


@dataclass
class DiceEvent(ShowConvertible):
    """Single DICE event or linkout item."""

    event_id: str
    name: str
    date: str
    venue: str
    timezone: str
    url: Optional[str] = None
    external_url: Optional[str] = None
    description: Optional[str] = None
    currency: str = "USD"
    price_cents: Optional[int] = None
    sold_out: bool = False
    ticket_type: str = "General Admission"
    flags: list[str] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "DiceEvent":
        ticket_types = data.get("ticket_types") or []
        first_ticket = next((ticket for ticket in ticket_types if isinstance(ticket, dict)), {})
        ticket_price = first_ticket.get("price") if isinstance(first_ticket, dict) else None
        price_cents = None
        if isinstance(ticket_price, dict) and ticket_price.get("total") is not None:
            price_cents = int(ticket_price["total"])
        elif data.get("price") is not None:
            price_cents = int(data["price"])

        sold_out = bool(data.get("sold_out"))
        if isinstance(first_ticket, dict) and first_ticket.get("sold_out") is not None:
            sold_out = sold_out or bool(first_ticket["sold_out"])

        return cls(
            event_id=str(data.get("id") or data.get("int_id") or ""),
            name=(data.get("name") or "").strip(),
            date=data.get("date") or "",
            venue=(data.get("venue") or "").strip(),
            timezone=data.get("timezone") or "",
            url=data.get("url"),
            external_url=data.get("external_url"),
            description=data.get("description") or data.get("raw_description"),
            currency=data.get("currency") or "USD",
            price_cents=price_cents,
            sold_out=sold_out,
            ticket_type=(first_ticket.get("name") or "General Admission")
            if isinstance(first_ticket, dict)
            else "General Admission",
            flags=list(data.get("flags") or []),
        )

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.name or not self.date:
            return None

        try:
            start_date = datetime.fromisoformat(self.date.replace("Z", "+00:00"))
        except ValueError:
            return None

        ticket_url = url or self.url or self.external_url or club.website
        price = self.price_cents / 100 if self.price_cents is not None else None
        tickets = [
            ShowFactoryUtils.create_fallback_ticket(
                ticket_url,
                price=price,
                ticket_type=self.ticket_type,
                sold_out=self.sold_out,
            )
        ]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=start_date,
            show_page_url=ticket_url,
            tickets=tickets,
            description=self.description,
            enhanced=enhanced,
        )
