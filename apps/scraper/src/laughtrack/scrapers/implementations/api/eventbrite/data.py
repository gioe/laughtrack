"""
Data model for scraped event data from the Eventbrite API.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.eventbrite import EventbriteEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class EventbriteVenueData(EventListContainer[EventbriteEvent]):
    """
    Generic container for events returned by the Eventbrite API for a venue or organizer.

    Holds the list of EventbriteEvent objects extracted from an Eventbrite API response.
    """

    event_list: List[EventbriteEvent]
