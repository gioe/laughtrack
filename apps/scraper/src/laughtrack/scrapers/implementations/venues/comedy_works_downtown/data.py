"""Data model for scraped page data from Comedy Works Downtown."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.comedy_works_downtown import ComedyWorksDowntownEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ComedyWorksDowntownPageData(EventListContainer[ComedyWorksDowntownEvent]):
    """Raw extracted data from Comedy Works Downtown pages."""

    event_list: List[ComedyWorksDowntownEvent]
