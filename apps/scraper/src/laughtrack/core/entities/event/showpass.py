"""
Data model for a single event from the Showpass public calendar API.

Venues using Showpass for ticketing publish upcoming shows via:

  GET https://www.showpass.com/api/public/venues/{slug}/calendar/
      ?only_parents=true&page_size=100
      &ends_on__gte={start}&starts_on__lt={end}

Each item in the ``results`` array represents one show with title, dates
(ISO 8601 with UTC offset), slug (for ticket URL), and sold-out status.

Comedian names are extracted from the event ``name`` field, which typically
follows the pattern "Performing <date> : <Comedian Name>".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.core.entities.ticket.model import Ticket

_NAME_RE = re.compile(r"^Performing\s+\w+\s+\d{1,2}\s*:\s*(.+)$", re.IGNORECASE)


@dataclass
class ShowpassOffer:
    """Retain source units, sale windows and fees without losing currency."""

    source: dict
    currency: str
    amount: Optional[Decimal]
    available: bool
    sold_out: bool
    individual_admission: bool
    fee_quotes: dict[str, dict[str, Decimal]] = field(default_factory=dict)

    def to_ticket(self, url: str) -> Ticket:
        label = self.source["name"]
        currency = self.currency or "currency unspecified"
        if self.amount is not None:
            label += f" ({currency} {self.amount} base)"
        for option, quote in self.fee_quotes.items():
            parts = []
            if "total_price_no_tax" in quote:
                parts.append(f"{currency} {quote['total_price_no_tax']} before tax")
            if "total_price" in quote:
                parts.append(f"{currency} {quote['total_price']} including tax")
            if parts:
                label += f" [web option {option}: {'; '.join(parts)}]"
        minimum = self.source.get("minimum_purchase_limit")
        if minimum:
            label += f" [minimum purchase {minimum}]"
        if not self.available:
            label += " [not currently purchasable]"
        # Currency-less Ticket.price feeds USD filters/minima. Source CAD and
        # package totals remain labeled evidence, never converted or divided.
        price = self.amount if self.currency == "USD" and self.available and self.individual_admission else None
        return Ticket(
            price=float(price) if price is not None else None, purchase_url=url, sold_out=self.sold_out, type=label
        )


@dataclass
class ShowpassEvent(ShowConvertible):
    """A single Showpass calendar event."""

    event_id: int
    name: str
    slug: str
    starts_on: str  # ISO 8601 e.g. "2026-04-14T01:30:00+00:00"
    ends_on: str
    timezone: str  # IANA e.g. "America/Edmonton"
    sold_out: bool = False
    status: str = ""
    description: str = ""
    offers: list[ShowpassOffer] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict) -> ShowpassEvent:
        """Create a ShowpassEvent from a Showpass calendar API dict."""
        return cls(
            event_id=int(data.get("id", 0)),
            name=(data.get("name") or "").strip(),
            slug=(data.get("slug") or "").strip(),
            starts_on=data.get("starts_on") or "",
            ends_on=data.get("ends_on") or "",
            timezone=data.get("timezone") or "",
            sold_out=bool(data.get("sold_out", False)),
            status=data.get("status") or "",
            description=data.get("description") or "",
        )

    def _extract_comedian_name(self) -> str:
        """Extract comedian name from the event title.

        Handles patterns like:
          "Performing April 13 : Tre Stewart" -> "Tre Stewart"
          "Sunday Smoke Show" -> "" (no comedian)
          "The Workshop" -> "" (no comedian)
        """
        m = _NAME_RE.match(self.name)
        return m.group(1).strip() if m else ""

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert to a Show object."""
        from laughtrack.core.entities.comedian.model import Comedian
        from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

        if not self.name or not self.starts_on:
            return None

        try:
            start_date = datetime.fromisoformat(self.starts_on)
        except ValueError:
            return None

        ticket_url = f"https://www.showpass.com/{self.slug}/"
        tickets = [offer.to_ticket(ticket_url) for offer in self.offers] or [
            ShowFactoryUtils.create_fallback_ticket(ticket_url, sold_out=self.sold_out)
        ]

        # Use the club's website as show_page_url (drives traffic to venue).
        # scraping_url is the Showpass API URL, not suitable for display.
        show_page_url = url or (club.website or ticket_url)

        lineup = []
        comedian_name = self._extract_comedian_name()
        if comedian_name:
            lineup = [Comedian(name=comedian_name)]

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=start_date,
            show_page_url=show_page_url,
            lineup=lineup,
            tickets=tickets,
            enhanced=enhanced,
        )
