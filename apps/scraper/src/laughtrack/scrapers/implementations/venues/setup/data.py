"""Data model for scraped page data from The Setup."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.setup import SetupEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class SetupPageData(EventListContainer[SetupEvent]):
    """Raw extracted event data from The Setup's Google Sheets CSV."""

    event_list: List[SetupEvent]
