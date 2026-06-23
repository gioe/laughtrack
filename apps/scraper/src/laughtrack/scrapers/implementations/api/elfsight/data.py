"""Data model for scraped page data from an Elfsight Event Calendar widget."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.elfsight import ElfsightEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ElfsightPageData(EventListContainer[ElfsightEvent]):
    """Raw extracted event data from an Elfsight Event Calendar widget."""

    event_list: List[ElfsightEvent]
