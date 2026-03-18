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
    Data model representing raw extracted data from Grove34's Webflow site.
    Contains Grove34Event objects extracted from individual show detail pages.
    """

    event_list: List[Grove34Event]

    def has_event_data(self) -> bool:
        """Check if the scraped page contains any event data."""
        return bool(self.event_list)

    def get_event_count(self) -> int:
        """Get the number of events."""
        return len(self.event_list)
