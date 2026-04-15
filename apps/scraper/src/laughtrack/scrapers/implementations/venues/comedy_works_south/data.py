"""Data model for scraped page data from Comedy Works South."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.comedy_works_downtown import ComedyWorksDowntownEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ComedyWorksSouthPageData(EventListContainer[ComedyWorksDowntownEvent]):
    """Raw extracted data from Comedy Works South pages.

    Reuses ComedyWorksDowntownEvent since both locations share the same
    HTML structure and data model on comedyworks.com.
    """

    event_list: List[ComedyWorksDowntownEvent]
