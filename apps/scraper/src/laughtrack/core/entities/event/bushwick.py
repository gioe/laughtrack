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
        """Factory method to create a Show from a BushwickEvent and Club.

        Args:
            bushwick_event: The BushwickEvent instance to convert
            club: The Club instance for the show
            enhanced: Whether to use enhanced processing for tickets and tags
            source_url: Optional source URL for enhanced URL processing

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

        # Extract tickets from registration form
        tickets = []
        if self.registration_form:
            external_url = self.registration_form.get("externalRegistrationUrl", "")
            if external_url:
                tickets.append(ShowFactoryUtils.create_fallback_ticket(external_url))

        # Create show page URL from registration form or use source_url
        show_page_url = ""
        if self.registration_form:
            show_page_url = self.registration_form.get("externalRegistrationUrl", "")
    # source_url removed; keep computed show_page_url only

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
