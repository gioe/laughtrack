"""
Data model for scraped page data from Gotham Comedy Club.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.gotham import GothamEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class GothamPageData(EventListContainer[GothamEvent]):
    """
    Data model representing raw extracted data from Gotham Comedy Club's S3 JSON API.

    This contains the GothamEvent objects extracted from the monthly JSON files,
    following the standard PageData pattern.
    """

    event_list: List[GothamEvent]
