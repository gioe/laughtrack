"""Data model for scraped page data from The Comedy & Magic Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.comedy_magic_club import ComedyMagicClubEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ComedyMagicClubPageData(EventListContainer[ComedyMagicClubEvent]):
    """Raw extracted event data from The Comedy & Magic Club listing page."""

    event_list: List[ComedyMagicClubEvent]
