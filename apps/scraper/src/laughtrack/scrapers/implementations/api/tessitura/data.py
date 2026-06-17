"""Data model for Tessitura WordPress scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tessitura import TessituraEvent


@dataclass
class TessituraPageData:
    """Container for comedy productions extracted from a Tessitura WP feed."""

    event_list: List[TessituraEvent]
