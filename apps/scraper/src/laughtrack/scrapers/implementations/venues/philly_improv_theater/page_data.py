"""Data model for scraped PHIT Crowdwork API response."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.philly_improv import PhillyImprovShow
from laughtrack.ports.scraping import EventListContainer


@dataclass
class PhillyImprovPageData(EventListContainer[PhillyImprovShow]):
    """Raw extracted data from the PHIT Crowdwork API (one entry per performance)."""

    event_list: List[PhillyImprovShow]
