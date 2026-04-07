"""Page data container for the generic SquadUP platform scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.squadup import SquadUpEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class SquadUpPageData(EventListContainer[SquadUpEvent]):
    """Raw extracted event data from the SquadUP API."""

    event_list: List[SquadUpEvent]
