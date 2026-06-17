"""Data model for Playhouse Square scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.playhouse_square import PlayhouseSquareEvent


@dataclass
class PlayhouseSquarePageData:
    """Container for comedy events extracted from the Playhouse Square feed."""

    event_list: List[PlayhouseSquareEvent]
