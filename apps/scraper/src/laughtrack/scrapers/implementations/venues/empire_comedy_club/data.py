"""Data model for scraped page data from Empire Comedy Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.empire import EmpireEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class EmpirePageData(EventListContainer[EmpireEvent]):
    """Raw extracted data from Empire Comedy Club's shows listing page."""

    event_list: List[EmpireEvent]
