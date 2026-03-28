"""Data model for scraped Logan Square Improv Crowdwork API response."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.philly_improv import PhillyImprovShow
from laughtrack.ports.scraping import EventListContainer


@dataclass
class LoganSquareImprovPageData(EventListContainer[PhillyImprovShow]):
    """Raw extracted data from the Logan Square Improv Crowdwork API (one entry per performance)."""

    event_list: List[PhillyImprovShow]
