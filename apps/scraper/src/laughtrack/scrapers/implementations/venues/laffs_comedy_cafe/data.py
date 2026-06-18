"""Data model for scraped page data from Laffs Comedy Cafe."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.laffs_comedy_cafe import LaffsComedyCafeEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class LaffsComedyCafePageData(EventListContainer[LaffsComedyCafeEvent]):
    """Raw extracted event data from the Laffs Comedy Cafe coming-soon page."""

    event_list: List[LaffsComedyCafeEvent]
