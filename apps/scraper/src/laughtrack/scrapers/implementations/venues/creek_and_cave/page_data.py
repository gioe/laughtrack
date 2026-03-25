"""Data model for scraped page data from The Creek and The Cave."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.creek_and_cave import CreekAndCaveEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class CreekAndCavePageData(EventListContainer[CreekAndCaveEvent]):
    """
    Container for CreekAndCaveEvent objects extracted from an S3 monthly JSON file.

    Follows the standard PageData pattern for the 5-component architecture.
    """

    event_list: List[CreekAndCaveEvent]
