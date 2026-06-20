"""Page data for BrassTix calendar responses."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.brasstix import BrassTixEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class BrassTixPageData(EventListContainer[BrassTixEvent]):
    event_list: List[BrassTixEvent]
