"""Page data model for Flappers scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.flappers import FlappersEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class FlappersPageData(EventListContainer[FlappersEvent]):
    """Raw extracted data from a single Flappers calendar month page."""

    event_list: List[FlappersEvent]
