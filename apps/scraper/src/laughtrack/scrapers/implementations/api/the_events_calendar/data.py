"""Data model for scraped page data from a The Events Calendar (Tribe) site."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tribe_events import TribeEvent


@dataclass
class TribeEventsPageData:
    """Raw extracted event data from a Tribe Events REST API."""

    event_list: List[TribeEvent]
