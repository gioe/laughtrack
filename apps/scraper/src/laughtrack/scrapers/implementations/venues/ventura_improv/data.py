"""Data model for scraped page data from the Ventura Improv /shows page."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.ventura_improv import VenturaImprovEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class VenturaImprovPageData(EventListContainer[VenturaImprovEvent]):
    """Raw extracted show rows from the Ventura Improv 'Coming Up' block."""

    event_list: List[VenturaImprovEvent]
