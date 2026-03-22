"""Page data model for Goofs Comedy Club scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.goofs import GoofsEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class GoofsPageData(EventListContainer[GoofsEvent]):
    """Raw extracted data from the Goofs Comedy Club /p/shows listing page."""

    event_list: List[GoofsEvent]
