"""Page data container for the StandUp Media platform scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.standup_media import StandUpMediaEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class StandUpMediaPageData(EventListContainer[StandUpMediaEvent]):
    """Raw extracted show data from the StandUp Media reservation API."""

    event_list: List[StandUpMediaEvent]
