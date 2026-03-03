"""
Data model for scraped page data from Rodney's Comedy Club.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.rodneys import RodneyEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class RodneyPageData(EventListContainer[RodneyEvent]):
    """
    Data model representing raw extracted data from Rodney's Comedy Club pages.

    This contains the RodneyEvent objects extracted from various sources:
    - Direct HTML pages with JSON-LD
    - Eventbrite API responses
    - 22Rams API responses

    Follows the standard PageData pattern for the 5-component architecture.
    """

    event_list: List[RodneyEvent]
