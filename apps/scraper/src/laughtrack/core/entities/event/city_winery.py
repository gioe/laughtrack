"""City Winery API event model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import pytz

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.model import Ticket
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

_TICKET_BASE_URL = "https://tickets.citywinery.com/event"


def _parse_iso_datetime(value: str, timezone_name: str) -> Optional[datetime]:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None

    try:
        return parsed.astimezone(pytz.timezone(timezone_name))
    except Exception:
        return parsed


def _ticket_url(slug: str) -> str:
    return f"{_TICKET_BASE_URL}/{slug.strip('/')}"


def _is_sold_out(sale_status: str, availability_indicator: str) -> bool:
    normalized_status = (sale_status or "").lower()
    normalized_availability = (availability_indicator or "").lower()
    return normalized_status in {"soldout", "sold_out", "sold out"} or normalized_availability == "red"


@dataclass
class CityWineryEvent(ShowConvertible):
    """A single event returned by ``https://awsapi.citywinery.com/events``."""

    event_id: str
    slug: str
    name: str
    start: str
    end: str = ""
    timezone: str = "UTC"
    location_name: str = ""
    location_street: str = ""
    location_city: str = ""
    location_postal: str = ""
    location_country: str = ""
    currency: str = "USD"
    starting_price: Optional[float] = None
    sale_status: str = ""
    availability_indicator: str = ""
    image: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Optional["CityWineryEvent"]:
        slug = str(raw.get("url") or "").strip()
        name = str(raw.get("name") or "").strip()
        start = str(raw.get("start") or "").strip()
        event_id = str(raw.get("_id") or raw.get("id") or "").strip()
        if not slug or not name or not start:
            return None

        seo_settings = raw.get("seoSettings") or {}
        if not isinstance(seo_settings, dict):
            seo_settings = {}

        raw_tags = seo_settings.get("tags") or []
        tags = [str(tag) for tag in raw_tags if tag]

        raw_attributes = raw.get("attributes") or {}
        attributes = raw_attributes if isinstance(raw_attributes, dict) else {}

        return cls(
            event_id=event_id,
            slug=slug,
            name=name,
            start=start,
            end=str(raw.get("end") or ""),
            timezone=str(raw.get("timezone") or "UTC"),
            location_name=str(raw.get("locationName") or ""),
            location_street=str(raw.get("locationStreet") or ""),
            location_city=str(raw.get("locationCity") or ""),
            location_postal=str(raw.get("locationPostal") or ""),
            location_country=str(raw.get("locationCountry") or ""),
            currency=str(raw.get("currency") or "USD"),
            starting_price=_safe_float(raw.get("startingPrice")),
            sale_status=str(raw.get("saleStatus") or ""),
            availability_indicator=str(raw.get("availabilityIndicator") or ""),
            image=str(raw.get("image") or ""),
            description=str(seo_settings.get("description") or ""),
            tags=tags,
            attributes=attributes,
        )

    def to_show(self, club: Club, enhanced: bool = True, url: Optional[str] = None) -> Optional[Show]:
        timezone_name = self.timezone or club.timezone or "UTC"
        start_dt = _parse_iso_datetime(self.start, timezone_name)
        if start_dt is None:
            return None

        purchase_url = url or _ticket_url(self.slug)
        room = str(self.attributes.get("stage") or self.location_name or "")
        ticket_type = f"General Admission ({self.currency})" if self.currency else "General Admission"
        tickets = [
            Ticket(
                price=self.starting_price if self.starting_price is not None else 0.0,
                purchase_url=purchase_url,
                sold_out=_is_sold_out(self.sale_status, self.availability_indicator),
                type=ticket_type,
            )
        ]

        supplied_tags = ["event", "city_winery"]
        supplied_tags.extend(tag for tag in self.tags if tag)

        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.name,
            club=club,
            date=start_dt,
            show_page_url=purchase_url,
            lineup=[],
            tickets=tickets,
            description=self.description,
            room=room,
            supplied_tags=supplied_tags,
            enhanced=enhanced,
        )


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
