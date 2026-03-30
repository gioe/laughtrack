"""
Data model for a single event from a Ninkashi-powered venue.

Show data is fetched from the Ninkashi public JSON API:
  GET https://api.ninkashi.com/public_access/events/find_by_url_site
      ?url_site=<subdomain>&page=1&per_page=100

Key response fields per event:
- id              — unique integer event ID
- title           — event name
- time_zone       — IANA timezone string (e.g. "America/Los_Angeles")
- event_dates_attributes — array with one entry; its starts_at field holds the event
                           datetime as "YYYY-MM-DD HH:MM:SS ±HHMM" (space-separated,
                           4-digit offset, e.g. "2026-04-01 19:45:00 -0700")
- tickets_attributes — array of ticket tier objects; price is in cents (2500 = $25.00),
                       tier name is in the "description" field (not "name")

Ticket purchase URL is constructed as https://{url_site}/events/{id}.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


def _parse_ninkashi_datetime(starts_at: str, time_zone: str) -> Optional[datetime]:
    """
    Parse a Ninkashi starts_at string and return a timezone-aware datetime.

    The Ninkashi API returns starts_at inside event_dates_attributes in the format
    "2026-04-01 19:45:00 -0700" (space-separated, no colon in offset).
    We parse the offset-aware datetime and convert it to the venue's IANA timezone.
    Returns None if parsing fails.
    """
    try:
        tz = pytz.timezone(time_zone)
        dt = datetime.strptime(starts_at, "%Y-%m-%d %H:%M:%S %z")
        return dt.astimezone(tz)
    except Exception:
        return None


@dataclass
class NinkashiTicket:
    """A single ticket tier from the Ninkashi tickets_attributes array."""

    price: Optional[float]
    sold_out: bool
    name: str
    remaining_tickets: Optional[int]

    @classmethod
    def from_dict(cls, data: dict) -> "NinkashiTicket":
        raw_price = data.get("price")
        try:
            # Ninkashi API returns price in cents (e.g. 2500 = $25.00)
            price = float(raw_price) / 100.0 if raw_price is not None else 0.0
        except (ValueError, TypeError):
            price = 0.0
        return cls(
            price=price,
            sold_out=bool(data.get("sold_out", False)),
            # Ninkashi uses "description" for the ticket tier name
            name=str(data.get("description") or data.get("name") or "General Admission"),
            remaining_tickets=data.get("remaining_tickets"),
        )


@dataclass
class NinkashiEvent(ShowConvertible):
    """A single event from the Ninkashi public API."""

    id: int
    title: str
    starts_at: str           # extracted from event_dates_attributes[0].starts_at,
                             # format: "YYYY-MM-DD HH:MM:SS ±HHMM" e.g. "2026-04-01 19:45:00 -0700"
    time_zone: str           # IANA timezone, e.g. "America/Los_Angeles"
    url_site: str            # The url_site used to fetch this event, e.g. "tickets.cttcomedy.com"
    tickets_attributes: List[NinkashiTicket] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict, url_site: str) -> "NinkashiEvent":
        raw_tickets = data.get("tickets_attributes") or []
        tickets = [NinkashiTicket.from_dict(t) for t in raw_tickets if isinstance(t, dict)]
        # starts_at is nested under event_dates_attributes[0], not at the top level
        event_dates = data.get("event_dates_attributes") or []
        first_date = event_dates[0] if event_dates else {}
        starts_at = str(first_date.get("starts_at", ""))
        return cls(
            id=int(data["id"]),
            title=str(data.get("title", "")),
            starts_at=starts_at,
            time_zone=str(data.get("time_zone", "UTC")),
            url_site=url_site,
            tickets_attributes=tickets,
        )

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert a NinkashiEvent to a Show domain object."""
        if not self.title or not self.starts_at:
            return None

        start_dt = _parse_ninkashi_datetime(self.starts_at, self.time_zone or club.timezone or "UTC")
        if start_dt is None:
            return None

        ticket_url = url or f"https://{self.url_site}/events/{self.id}"

        tickets: List[Ticket] = []
        if self.tickets_attributes:
            for t in self.tickets_attributes:
                tickets.append(
                    Ticket(
                        price=t.price or 0.0,
                        purchase_url=ticket_url,
                        sold_out=t.sold_out,
                        type=t.name,
                    )
                )
        else:
            tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_url)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_dt,
            show_page_url=ticket_url,
            lineup=[],
            tickets=tickets,
            enhanced=enhanced,
        )
