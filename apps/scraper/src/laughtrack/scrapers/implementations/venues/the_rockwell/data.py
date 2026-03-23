"""Data model for scraped page data from The Rockwell."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.rockwell import RockwellEvent


@dataclass
class RockwellPageData:
    """Raw extracted event data from The Rockwell's Tribe Events REST API."""

    event_list: List[RockwellEvent]
