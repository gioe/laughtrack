from dataclasses import dataclass
from typing import Optional


from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.entities.ticket.local.grove34 import Grove34Ticket
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils
from laughtrack.foundation.infrastructure.logger.logger import Logger


@dataclass
class Grove34Event:
    """
    Data model representing a single event from Grove34's Wix warmup data.

    This corresponds to the event structure found in Wix Events platform embedded
    in the script tag with id="wix-warmup-data".
    """

    # Core event information
    id: str
    title: str
    slug: str
    # Scheduling information
    start_date: str  # ISO format datetime string
    timezone_id: str  # e.g., "America/New_York"
    description: Optional[str] = None

    # Location information
    location_name: Optional[str] = None

    # Registration/ticketing information
    ticketing_data: Optional[dict] = None  # Raw ticketing info from registration
    sold_out: bool = False
    lowest_price: Optional[float] = None
    highest_price: Optional[float] = None

    # Raw event data for debugging/future use
    raw_event_data: Optional[dict] = None

    def to_show(self, club: Club, enhanced: bool = True) -> Optional[Show]:
        """Factory method to create a Show from a Grove34Event and Club.

        Args:
            grove34_event: The Grove34Event instance to convert
            club: The Club instance for the show
            enhanced: Whether to use enhanced processing for tickets and tags
            source_url: Optional source URL for enhanced URL processing

        Returns:
            Show: A new Show instance created from the Grove34Event, or None if conversion fails
        """
        try:
            # Parse datetime
            clean_date_str = self.start_date.split(".")[0] + "Z"
            event_datetime = ShowFactoryUtils.parse_wix_iso_date(clean_date_str, self.timezone_id)
            if not event_datetime:
                return None

            # Create show page URL
            show_page_url = f"https://grove34.com/event/{self.slug}" if self.slug else ""

            # Extract ticket information
            tickets = Grove34Ticket.create_tickets_from_grove34_event(
                lowest_price=self.lowest_price,
                highest_price=self.highest_price,
                purchase_url=show_page_url,
                sold_out=self.sold_out,
            )

            # Extract comedian lineup (Grove34 doesn't provide structured lineup data)
            lineup = []  # Grove34 events don't contain structured lineup information

            # Create standardized show
            return ShowFactoryUtils.create_enhanced_show_base(
                name=self.title,
                club=club,
                date=event_datetime,
                show_page_url=show_page_url,
                lineup=lineup,
                tickets=tickets,
                description=self.description,
                room=self.location_name or "",
                supplied_tags=["event"],
                enhanced=enhanced,
            )

        except Exception as e:
            Logger.error(f"Error converting Grove34Event to show: {e}")
            return None
