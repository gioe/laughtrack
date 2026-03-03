"""
Data model for scraped page data from Grove34 (grove34.com).
"""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.grove34 import Grove34Event
from laughtrack.ports.scraping import EventListContainer


@dataclass
class Grove34PageData(EventListContainer[Grove34Event]):
    """
    Data model representing raw extracted data from Grove34's Wix Events platform.

    This contains the Grove34Event objects extracted from the Wix warmup data
    script tag, following the standard PageData pattern.
    """

    event_list: List[Grove34Event]

    def has_event_data(self) -> bool:
        """Check if the scraped page contains any event data."""
        return bool(self.event_list)

    def get_event_count(self) -> int:
        """Get the number of events found in the warmup data."""
        return len(self.event_list)

    def get_event_ids(self) -> List[str]:
        """Get list of event IDs."""
        return [event.id for event in self.event_list if event.id]

    def get_event_titles(self) -> List[str]:
        """Get list of event titles."""
        return [event.title for event in self.event_list if event.title]

    def get_events_with_tickets(self) -> List[Grove34Event]:
        """Get events that have ticket pricing information."""
        return [
            event
            for event in self.event_list
            if event.ticketing_data and (event.lowest_price is not None or event.highest_price is not None)
        ]

    def get_sold_out_events(self) -> List[Grove34Event]:
        """Get events that are marked as sold out."""
        return [event for event in self.event_list if event.sold_out]
