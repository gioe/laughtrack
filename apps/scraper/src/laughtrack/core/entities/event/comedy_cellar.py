from dataclasses import dataclass
from typing import List, Optional

from laughtrack.foundation.models.api.comedy_cellar.models import ShowInfoData
from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible
from laughtrack.utilities.domain.show.factory import ShowFactoryUtils


@dataclass
class ComedyCellarEvent(ShowConvertible):
    """
    Data model representing a single show from Comedy Cellar's multi-step API workflow.

    This combines data from both the lineup API (HTML) and shows API (JSON) into
    a unified event structure that can be converted to a Show object.
    """

    # Core show information
    show_id: int
    date_key: str  # Date in YYYY-MM-DD format
    api_time: str  # Time from API in HH:MM:SS format
    show_name: str
    description: Optional[str]
    note: Optional[str]

    # Room information
    room_id: Optional[int]
    room_name: Optional[str]

    # Ticket information from API
    timestamp: int
    ticket_link: str
    ticket_data: ShowInfoData  # Raw API ticket data

    # Lineup information from HTML
    html_container: Optional[str]  # BeautifulSoup container as string
    lineup_names: Optional[List[str]] = None  # Extracted comedian names

    def __post_init__(self):
        """Initialize lineup_names if not provided."""
        if self.lineup_names is None:
            self.lineup_names = []

    def to_show(self, club: Club, enhanced: bool = True) -> Optional[Show]:
        """Factory method to create a Show from a ComedyCellarEvent and Club.

        Args:
            comedy_cellar_event: The ComedyCellarEvent instance to convert
            club: The Club instance for the show
            enhanced: Whether to use enhanced processing for tickets and tags
            source_url: Optional source URL for enhanced URL processing

        Returns:
            Show: A new Show instance created from the ComedyCellarEvent
        """

        # Parse event datetime from date_key and api_time
        datetime_str = f"{self.date_key} {self.api_time}"
        start_date = ShowFactoryUtils.safe_parse_datetime_string(datetime_str, "%Y-%m-%d %H:%M:%S", "America/New_York")

        if not start_date:
            raise ValueError(f"No valid start_date found for Comedy Cellar event")

        # Create lineup from lineup_names
        lineup = ShowFactoryUtils.create_lineup_from_performers(self.lineup_names or [])

        # Create tickets from API data
        tickets = []
        if self.ticket_data:
            # Extract ticket information from the API data
            ticket_price = ShowFactoryUtils.safe_float_conversion(self.ticket_data.cover)

            tickets.append(
                ShowFactoryUtils.create_fallback_ticket(
                    purchase_url=self.ticket_link,
                    price=ticket_price,
                    ticket_type="General Admission",
                    sold_out=False,  # Could be enhanced to check API status
                )
            )

        # Determine room name using standardized room mapping
        room_map = {1: "MacDougal St.", 2: "Village Underground", 3: "Fat Black Pussycat"}
        room = ""
        if self.room_name:
            room = self.room_name
        elif self.room_id is not None:
            room = room_map.get(self.room_id, f"Room {self.room_id}")

        # Build show page URL
        show_page_url = (
            f"https://www.comedycellar.com/reservations-newyork/?showid={self.show_id}"
            if self.show_id
            else "https://www.comedycellar.com/reservations-newyork/"
        )

        # Create standardized show
        return ShowFactoryUtils.create_enhanced_show_base(
            name=self.show_name,
            club=club,
            date=start_date,
            show_page_url=show_page_url,
            lineup=lineup,
            tickets=tickets,
            description=self.description or self.note,
            room=room,
            supplied_tags=["comedy"],
            enhanced=enhanced,
        )
