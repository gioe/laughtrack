"""Page data container for the Dojour platform scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.dojour import DojourEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class DojourPageData(EventListContainer[DojourEvent]):
    """Raw extracted showing data from the Dojour user_feed API."""

    event_list: List[DojourEvent]
