"""
Extractor stub for Eventbrite API.

API scrapers typically fetch via dedicated clients; this module exists to
conform to the 5-file scraper structure and can host parsing helpers.
"""

from typing import List

from laughtrack.core.entities.event.eventbrite import EventbriteEvent


class EventbriteExtractor:
    @staticmethod
    def to_page_data(events: List[EventbriteEvent]):
        from .data import EventbriteVenueData

        return EventbriteVenueData(event_list=events)
