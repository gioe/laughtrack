from dataclasses import dataclass
from typing import Any, Dict, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils

@dataclass
class BushwickEvent(ShowConvertible):
    """
    Data model representing a single event from Bushwick Comedy Club's Wix API.

    This corresponds to the JSON structure returned by their Wix events endpoint.
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

    # Raw event data for reference
    _raw_data: Optional[Dict[str, Any]] = None

    def to_show(self, club: Club, enhanced: bool = True) -> Optional[Show]:
        """Convert a BushwickEvent to a Show domain object.

        Args:
            club: The Club instance for the show
            enhanced: Whether to use enhanced processing for tickets and tags

        Returns:
            Show: A new Show instance created from the BushwickEvent
        """

        # Parse event date from Wix scheduling data (required)
        start_date = None
        if self.scheduling:
            scheduling_config = self.scheduling.get("config", {})
            date_str = scheduling_config.get("startDate")
            if date_str:
                start_date = ShowFactoryUtils.parse_wix_iso_date(date_str, club.timezone or "UTC")

        if not start_date:
            raise ValueError("No valid start_date found for Bushwick event")

        # Construct event URL from slug — Wix event pages follow {base_url}/events/{slug}
        event_slug = self.registration_form.get("eventSlug", "") if self.registration_form else ""
        show_page_url = f"{club.scraping_url.rstrip('/')}/events/{event_slug}" if event_slug else ""

        # Extract tickets from event URL
        tickets = []
        if show_page_url:
            tickets.append(ShowFactoryUtils.create_fallback_ticket(show_page_url))

        # Extract title
        name = self.title.strip() if self.title else "Comedy Show"

        # Create standardized show
        return ShowFactoryUtils.create_enhanced_show_base(
            name=name,
            club=club,
            date=start_date,
            show_page_url=show_page_url,
            lineup=[],  # Basic extraction - Wix data structure doesn't have structured performer data
            tickets=tickets,
            description=self.description if self.description else None,
            room="",
            supplied_tags=["event"],
            enhanced=enhanced,
        )
