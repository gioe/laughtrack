"""Data model for NeonCRM scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.neoncrm import NeonCRMEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class NeonCRMPageData(EventListContainer[NeonCRMEvent]):
    """Container for events extracted from a NeonCRM eventList.jsp page."""

    event_list: List[NeonCRMEvent]
