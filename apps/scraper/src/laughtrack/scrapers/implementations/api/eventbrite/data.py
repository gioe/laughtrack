"""
Data model for scraped page data from Comedy Cellar.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.eventbrite import EventbriteEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class EventbriteVenueData(EventListContainer[EventbriteEvent]):
    """
    Data model representing raw extracted data from Comedy Cellar API responses.

    This contains the combined data from Comedy Cellar's multi-step API workflow:
    - lineup_data: HTML lineup data from the lineup API endpoint
    - shows_data: Structured show data from the getShows API endpoint
    - date: The date key for which this data was extracted
    """

    event_list: List[EventbriteEvent]
