"""Data model for scraped page data from a VBO Tickets ListEvents listing."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.vbo_tickets import VboEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class VboTicketsPageData(EventListContainer[VboEvent]):
    """Raw extracted event rows from a VBO Tickets ``showevents`` listing."""

    event_list: List[VboEvent]
