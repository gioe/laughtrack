"""
Data model for scraped page data from Uncle Vinnie's Comedy Club.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.uncle_vinnies import UncleVinniesEvent



@dataclass
class UncleVinniesPageData:
    """
    Data model representing raw extracted data from Uncle Vinnie's multi-step scraping.

    This contains the UncleVinniesEvent objects extracted from OvationTix API responses
    after calendar discovery and production ID extraction.
    """

    event_list: List[UncleVinniesEvent]

    def has_json_ld_data(self) -> bool:
        """Check if the scraped data contains any event data."""
        return bool(self.event_list)

    def get_event_count(self) -> int:
        """Get the number of events found."""
        return len(self.event_list)

    def get_events_with_tickets(self) -> List[UncleVinniesEvent]:
        """Get only events that have ticket information available."""
        return [event for event in self.event_list if event.has_ticket_data()]
