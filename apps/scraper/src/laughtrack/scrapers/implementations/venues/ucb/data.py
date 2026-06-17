"""Page data for Upright Citizens Brigade."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.ucb import UCBEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class UCBPageData(EventListContainer[UCBEvent]):
    event_list: List[UCBEvent]
