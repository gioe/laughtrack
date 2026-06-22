"""Timely calendar event model."""

from dataclasses import dataclass
import re
from typing import Any, Dict, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class TimelyEvent(ShowConvertible):
    """One event instance from events.timely.fun."""

    id: str
    title: str
    start_datetime: str
    timezone: str
    instance: str
    custom_url: str
    calendar_url: str
    description: Optional[str] = None
    cost_external_url: Optional[str] = None
    tickets_min_price: Optional[str] = None
    ticket_type: Optional[str] = None
    room: str = ""

    @classmethod
    def from_api(cls, raw: Dict[str, Any], calendar_url: str) -> Optional["TimelyEvent"]:
        title = str(raw.get("title") or "").strip()
        start_datetime = str(raw.get("start_datetime") or "").strip()
        if not title or not start_datetime:
            return None

        description = raw.get("description") or raw.get("description_short")
        return cls(
            id=str(raw.get("id") or ""),
            title=title,
            start_datetime=start_datetime,
            timezone=str(raw.get("timezone") or "America/New_York"),
            instance=str(raw.get("instance") or ""),
            custom_url=str(raw.get("custom_url") or ""),
            calendar_url=calendar_url.rstrip("/"),
            description=_clean_description(description),
            cost_external_url=str(raw.get("cost_external_url") or "").strip() or None,
            tickets_min_price=str(raw.get("tickets_min_price") or "").strip() or None,
            ticket_type=str(raw.get("ticket_type") or "").strip() or None,
            room=_venue_title(raw),
        )

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        start_date = ShowFactoryUtils.parse_datetime_with_timezone_fallback(
            self.start_datetime,
            self.timezone or club.timezone or "America/New_York",
        )
        show_page_url = url or self.show_page_url
        ticket_url = self.cost_external_url or show_page_url
        price = _parse_price(self.tickets_min_price)
        ticket = ShowFactoryUtils.create_fallback_ticket(ticket_url, price=price)

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.title,
            club=club,
            date=start_date,
            show_page_url=show_page_url,
            lineup=[],
            tickets=[ticket],
            description=self.description,
            room=self.room,
            supplied_tags=["event"],
            enhanced=enhanced,
        )

    @property
    def show_page_url(self) -> str:
        if self.calendar_url and self.custom_url and self.instance:
            return f"{self.calendar_url}/event/{quote(self.custom_url)}/{quote(self.instance)}"
        if self.calendar_url and self.id and self.instance:
            return f"{self.calendar_url}/event/{quote(self.id)}/{quote(self.instance)}"
        return self.calendar_url


def _clean_description(raw: Any) -> Optional[str]:
    if not raw:
        return None
    text = BeautifulSoup(str(raw), "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _parse_price(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    match = re.search(r"\d+(?:\.\d{1,2})?", raw.replace(",", ""))
    if not match:
        return None
    value = float(match.group(0))
    return value if value > 0 else None


def _venue_title(raw: Dict[str, Any]) -> str:
    taxonomies = raw.get("taxonomies")
    if not isinstance(taxonomies, dict):
        return ""
    venues = taxonomies.get("taxonomy_venue")
    if not isinstance(venues, list) or not venues:
        return ""
    first = venues[0]
    if not isinstance(first, dict):
        return ""
    return str(first.get("title") or "").strip()

