"""Data model for scraped iO Theater Crowdwork API response."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.philly_improv import PhillyImprovShow
from laughtrack.ports.scraping import EventListContainer


@dataclass
class IOTheaterPageData(EventListContainer[PhillyImprovShow]):
    """Raw extracted data from the iO Theater Crowdwork API (one entry per performance)."""

    event_list: List[PhillyImprovShow]
