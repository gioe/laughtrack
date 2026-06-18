"""Data model for scraped page data from McCurdy's Comedy Theatre."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.mccurdys_comedy_theatre import McCurdysEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class McCurdysPageData(EventListContainer[McCurdysEvent]):
    """Raw extracted event data from a McCurdy's Comedy Theatre detail page."""

    event_list: List[McCurdysEvent]
