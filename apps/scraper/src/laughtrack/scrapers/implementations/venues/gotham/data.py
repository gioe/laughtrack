"""
Data model for scraped page data from Gotham Comedy Club.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.core.clients.gotham.models.models import GothamFeedEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class GothamPageData(EventListContainer[GothamFeedEvent]):
    """
    Data model representing raw extracted data from Gotham Comedy Club's
    live events feed.

    This contains the GothamFeedEvent objects extracted from a feed page,
    following the standard PageData pattern.
    """

    event_list: List[GothamFeedEvent]
