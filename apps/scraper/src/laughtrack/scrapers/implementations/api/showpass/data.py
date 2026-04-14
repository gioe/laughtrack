"""Page data model for the generic Showpass scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.showpass import ShowpassEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ShowpassPageData(EventListContainer[ShowpassEvent]):
    """Raw extracted data from the Showpass public calendar API."""

    event_list: List[ShowpassEvent]
