"""Data model for scraped page data from The Bit Theater."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.the_bit_theater import BitTheaterEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class BitTheaterPageData(EventListContainer[BitTheaterEvent]):
    """Raw extracted event data from The Bit Theater Odoo event pages."""

    event_list: List[BitTheaterEvent]
