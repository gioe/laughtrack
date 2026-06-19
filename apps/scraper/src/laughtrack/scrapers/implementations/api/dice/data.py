"""Page data model for the generic DICE scraper."""

from dataclasses import dataclass
from typing import List, Optional

from laughtrack.core.entities.event.dice import DiceEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class DicePageData(EventListContainer[DiceEvent]):
    """Raw extracted data from one DICE partner API page."""

    event_list: List[DiceEvent]
    next_url: Optional[str] = None
