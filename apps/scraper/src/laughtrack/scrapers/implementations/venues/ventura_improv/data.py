"""Data model for scraped page data from the Ventura Improv /shows page."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.ventura_improv import VenturaImprovEvent


@dataclass
class VenturaImprovPageData:
    """Raw extracted show rows from the Ventura Improv 'Coming Up' block."""

    event_list: List[VenturaImprovEvent]
