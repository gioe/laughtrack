"""Data model for scraped page data from Stevie Ray's Improv Company."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.stevie_rays import StevieRaysEvent


@dataclass
class StevieRaysPageData:
    """Raw extracted event data from the Stevie Ray's Comedy Cabaret ticketing page."""

    event_list: List[StevieRaysEvent]
