"""Data model for scraped page data from a VBO Tickets ListEvents listing."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.vbo_tickets import VboEvent


@dataclass
class VboTicketsPageData:
    """Raw extracted event rows from a VBO Tickets ``showevents`` listing."""

    event_list: List[VboEvent]
