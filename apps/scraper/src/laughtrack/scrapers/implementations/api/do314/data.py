"""Page data container for the do314 / DoStuff Media platform scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.do314 import Do314Event
from laughtrack.ports.scraping import EventListContainer


@dataclass
class Do314PageData(EventListContainer[Do314Event]):
    """Raw extracted event data from the do314 venue events API."""

    event_list: List[Do314Event]
