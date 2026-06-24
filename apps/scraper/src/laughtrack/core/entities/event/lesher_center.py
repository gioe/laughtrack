"""Lesher Center event model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from laughtrack.core.entities.club.model import Club
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

_PURCHASE_BASE_URL = "https://purchase.lesherartscenter.org/EventAvailability"


@dataclass
class LesherCenterEvent(ShowConvertible):
    """Single comedy event instance from Lesher's Spektrix event catalog."""

    title: str
    date_time: datetime
    event_id: str
    web_event_id: str = ""
    genre: str = ""
    presenter: str = ""
    description: str = ""
    sold_out: bool = False

    @property
    def purchase_url(self) -> str:
        return f"{_PURCHASE_BASE_URL}?{urlencode({'EventId': self.event_id})}"

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None):
        if not self.title or not self.date_time or not self.event_id:
            return None

        timezone_name = club.timezone or "America/Los_Angeles"
        show_date = self.date_time
        if show_date.tzinfo is None:
            show_date = show_date.replace(tzinfo=ZoneInfo(timezone_name))
        else:
            show_date = show_date.astimezone(ZoneInfo(timezone_name))

        ticket_url = url or self.purchase_url
        tickets = [
            ShowFactoryUtils.create_fallback_ticket(
                ticket_url,
                price=0.0,
                sold_out=self.sold_out,
            )
        ]

        description_parts = []
        if self.genre:
            description_parts.append(self.genre)
        if self.presenter:
            description_parts.append(f"Presenter: {self.presenter}")
        if self.description:
            description_parts.append(self.description)
        if self.web_event_id:
            description_parts.append(f"Spektrix web event ID: {self.web_event_id}")

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=show_date,
            show_page_url=self.purchase_url,
            lineup=[],
            tickets=tickets,
            description=ShowFactoryUtils.build_description_from_parts(description_parts),
            supplied_tags=["event", "comedy"],
            enhanced=enhanced,
        )
