"""Data model for a single event from RED ROOM Comedy Club's Wix API."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class RedRoomEvent(ShowConvertible):
    """
    Data model representing a single event from RED ROOM Comedy Club's Wix API.

    Mirrors BushwickEvent but uses club.timezone or "UTC" as the timezone
    fallback rather than a hardcoded venue-specific value — required for any
    entity that may be reused across multiple venues.
    """

    id: str
    title: str
    description: str
    scheduling: Dict[str, Any]
    location: Dict[str, Any]
    registration_form: Dict[str, Any]
    created_date: str
    updated_date: str
    status: str
    _raw_data: Optional[Dict[str, Any]] = None

    def to_show(self, club: Club, enhanced: bool = True) -> Optional[Show]:
        """Convert a RedRoomEvent to a Show domain object."""
        start_date = None
        if self.scheduling:
            scheduling_config = self.scheduling.get("config", {})
            date_str = scheduling_config.get("startDate")
            if date_str:
                tz_name = club.timezone or "UTC"
                start_date = ShowFactoryUtils.parse_wix_iso_date(date_str, tz_name)

        if not start_date:
            raise ValueError("No valid start_date found for RED ROOM event")

        tickets = []
        if self.registration_form:
            external_url = self.registration_form.get("externalRegistrationUrl", "")
            if external_url:
                tickets.append(ShowFactoryUtils.create_fallback_ticket(external_url))

        show_page_url = ""
        if self.registration_form:
            show_page_url = self.registration_form.get("externalRegistrationUrl", "")

        name = self.title.strip() if self.title else "Comedy Show"

        return ShowFactoryUtils.create_enhanced_show_base(
            name=name,
            club=club,
            date=start_date,
            show_page_url=show_page_url,
            lineup=[],
            tickets=tickets,
            description=self.description if self.description else None,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
