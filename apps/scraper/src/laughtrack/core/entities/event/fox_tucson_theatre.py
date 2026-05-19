"""Fox Tucson Theatre event model."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


_PRICE_RE = re.compile(r"\$([0-9]+(?:\.[0-9]{1,2})?)")


@dataclass
class FoxTucsonTheatreEvent(ShowConvertible):
    """Official event card from foxtucson.com."""

    title: str
    date_time: datetime
    show_page_url: str
    ticket_url: str
    price_text: str = ""
    subtitle: str = ""
    card_classes: List[str] = field(default_factory=list)
    spektrix_event_url: Optional[str] = None
    spektrix_web_event_id: Optional[str] = None
    spektrix_instance_ids: List[str] = field(default_factory=list)

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        """Convert a parsed Fox Tucson event to the canonical Show model."""
        if not self.title or not self.date_time:
            return None

        tz = pytz.timezone(club.timezone or "America/Phoenix")
        show_date = self.date_time
        if show_date.tzinfo is None:
            show_date = tz.localize(show_date)
        else:
            show_date = show_date.astimezone(tz)

        ticket_purchase_url = self.spektrix_event_url or self.ticket_url or self.show_page_url
        price = self._minimum_price()
        tickets = [ShowFactoryUtils.create_fallback_ticket(ticket_purchase_url, price=price)]

        performers = [self.title]
        lineup = ShowFactoryUtils.create_lineup_from_performers(performers)

        description_parts = []
        if self.subtitle:
            description_parts.append(self.subtitle)
        if self.price_text:
            description_parts.append(f"Ticket price text: {self.price_text}")
        if self.spektrix_instance_ids:
            description_parts.append(
                f"Spektrix instance IDs: {', '.join(self.spektrix_instance_ids)}"
            )

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=show_date,
            show_page_url=self.show_page_url or url or ticket_purchase_url,
            lineup=lineup,
            tickets=tickets,
            description=ShowFactoryUtils.build_description_from_parts(description_parts),
            supplied_tags=["event", "comedy"],
            enhanced=enhanced,
        )

    def _minimum_price(self) -> float:
        prices = []
        for match in _PRICE_RE.finditer(self.price_text or ""):
            try:
                prices.append(float(match.group(1)))
            except ValueError:
                continue
        return min(prices) if prices else 0.0
