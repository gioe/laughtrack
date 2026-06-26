"""Data model for Arts-People scraped event data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.arts_people import ArtsPeopleEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ArtsPeoplePageData(EventListContainer[ArtsPeopleEvent]):
    """Container for performances extracted from an Arts-People ?show= page."""

    event_list: List[ArtsPeopleEvent]
