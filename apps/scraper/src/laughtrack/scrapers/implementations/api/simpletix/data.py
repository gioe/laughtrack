"""Data container for SimpleTix scraper page data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.simpletix import SimpleTixEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class SimpleTixPageData(EventListContainer[SimpleTixEvent]):
    """Container for events extracted from a SimpleTix event page."""

    event_list: List[SimpleTixEvent]
