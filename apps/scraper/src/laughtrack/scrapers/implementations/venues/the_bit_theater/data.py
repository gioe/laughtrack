"""Data model for scraped page data from The Bit Theater."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.the_bit_theater import BitTheaterEvent


@dataclass
class BitTheaterPageData:
    """Raw extracted event data from The Bit Theater Odoo event pages."""

    event_list: List[BitTheaterEvent]
