"""Data model for NeonCRM scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.neoncrm import NeonCRMEvent


@dataclass
class NeonCRMPageData:
    """Container for events extracted from a NeonCRM eventList.jsp page."""

    event_list: List[NeonCRMEvent]
