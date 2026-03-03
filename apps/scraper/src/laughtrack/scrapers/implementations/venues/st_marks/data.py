"""
Data model for scraped page data from St. Marks Comedy Club.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tixr import TixrEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class StMarksPageData(EventListContainer[TixrEvent]):
    """
    Data model representing raw extracted data from St. Marks Comedy Club pages.

    This contains the TixrEvent objects extracted from Tixr URLs found on
    the St. Marks venue page.

    Follows the standard PageData pattern for the 5-component architecture.
    """

    event_list: List[TixrEvent]
    source_url: str  # The original page URL where Tixr URLs were found

    def has_event_data(self) -> bool:
        """Check if the scraped page contains any event data."""
        return bool(self.event_list)

    def get_event_count(self) -> int:
        """Get the number of events found on the page."""
        return len(self.event_list)

    def get_event_ids(self) -> List[str]:
        """Get list of Tixr event IDs."""
        return [event.event_id for event in self.event_list if event.event_id]

    def get_event_titles(self) -> List[str]:
        """Get list of event titles."""
        return [event.title for event in self.event_list if event.title]

    def get_source_urls(self) -> List[str]:
        """Get list of Tixr URLs."""
        return [event.source_url for event in self.event_list if event.source_url]

    def get_shows(self) -> List:
        """Get list of Show objects from TixrEvents."""

        return [event.show for event in self.event_list if event.show]
