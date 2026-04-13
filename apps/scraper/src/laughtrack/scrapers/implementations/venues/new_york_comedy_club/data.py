"""PageData for New York Comedy Club scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class NewYorkComedyClubPageData(EventListContainer[JsonLdEvent]):
    event_list: List[JsonLdEvent]
