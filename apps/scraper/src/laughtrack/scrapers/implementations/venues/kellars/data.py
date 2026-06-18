"""Data model for scraped page data from Kellar's: Modern Magic and Comedy Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.kellars import KellarsEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class KellarsPageData(EventListContainer[KellarsEvent]):
    """Raw extracted event data from Kellar's listing page."""

    event_list: List[KellarsEvent]
