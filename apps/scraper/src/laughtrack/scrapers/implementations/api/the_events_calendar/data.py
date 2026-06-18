"""Data model for scraped page data from a The Events Calendar (Tribe) site."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tribe_events import TribeEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TribeEventsPageData(EventListContainer[TribeEvent]):
    """Raw extracted event data from a Tribe Events REST API."""

    event_list: List[TribeEvent]
