"""
Data model representing a single event from Tixr's API response.

This model represents event data specifically returned by the TixrClient.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from laughtrack.core.entities.club.model import Club
from laughtrack.core.entities.show.model import Show
from laughtrack.core.protocols.show_convertible import ShowConvertible


@dataclass
class TixrEvent(ShowConvertible):
    """
    Data model representing a single event from Tixr API.

    This corresponds to the Show object structure returned by TixrClient.get_event_detail().
    Since TixrClient directly returns Show objects, this model serves as a wrapper
    to maintain consistency with the architecture pattern.
    """

    # Core event information
    show: Show  # The actual Show object from TixrClient
    source_url: str  # The Tixr URL where this event was found
    event_id: str  # The Tixr event ID

    # Raw data preservation for debugging
    _raw_tixr_url: Optional[str] = None

    @classmethod
    def from_tixr_show(cls, show: Show, source_url: str, event_id: str) -> "TixrEvent":
        """
        Create a TixrEvent from a Show object returned by TixrClient.

        Args:
            show: Show object from TixrClient
            source_url: Original Tixr URL
            event_id: Tixr event ID

        Returns:
            TixrEvent instance
        """
        return cls(show=show, source_url=source_url, event_id=event_id, _raw_tixr_url=source_url)

    @property
    def title(self) -> str:
        """Get the event title."""
        return self.show.name

    @property
    def date_time(self) -> datetime:
        """Get the event datetime."""
        return self.show.date

    @property
    def description(self) -> Optional[str]:
        """Get the event description."""
        return self.show.description

    def to_show(self, club: Club, enhanced: bool = True, source_url: Optional[str] = None) -> Optional[Show]:
        """
        Convert TixrEvent to Show object.

        Args:
            club: Club instance (unused since show already has club_id)
            enhanced: Whether to apply enhanced processing (unused for Tixr)
            source_url: Optional source URL override

        Returns:
            The wrapped Show object
        """
        # Since TixrEvent already wraps a Show object, we just return it
        # We could update the show_page_url if source_url is provided
        if source_url and source_url != self.show.show_page_url:
            # Create a new show with updated URL if needed
            return Show(
                name=self.show.name,
                club_id=self.show.club_id,
                date=self.show.date,
                show_page_url=source_url,
                lineup=self.show.lineup,
                tickets=self.show.tickets,
                supplied_tags=self.show.supplied_tags,
                description=self.show.description,
                timezone=self.show.timezone,
                room=self.show.room,
            )

        return self.show
