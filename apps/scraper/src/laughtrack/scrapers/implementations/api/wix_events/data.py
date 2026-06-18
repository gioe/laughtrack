"""Page data container for the generic Wix Events platform scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.wix_events import WixEventsEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class WixEventsPageData(EventListContainer[WixEventsEvent]):
    """Raw extracted event data from a Wix Events API."""

    event_list: List[WixEventsEvent]
