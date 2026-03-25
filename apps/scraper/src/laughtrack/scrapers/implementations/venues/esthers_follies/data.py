"""Data model for scraped page data from Esther's Follies."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.esthers_follies import EsthersFolliesEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class EsthersFolliesPageData(EventListContainer[EsthersFolliesEvent]):
    """
    Container for EsthersFolliesEvent objects extracted from the VBO Tickets
    date slider, following the standard PageData pattern.
    """

    event_list: List[EsthersFolliesEvent]
