"""Data model for scraped The Backline Crowdwork API response."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.philly_improv import PhillyImprovShow
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TheBacklinePageData(EventListContainer[PhillyImprovShow]):
    """Raw extracted data from The Backline Crowdwork API (one entry per performance)."""

    event_list: List[PhillyImprovShow]
