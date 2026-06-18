"""Data model for Tessitura WordPress scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tessitura import TessituraEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TessituraPageData(EventListContainer[TessituraEvent]):
    """Container for comedy productions extracted from a Tessitura WP feed."""

    event_list: List[TessituraEvent]
