"""Page data model for TK's events page scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.tks_comedy import TksComedyEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TksComedyPageData(EventListContainer[TksComedyEvent]):
    """Raw extracted TK's comedy events."""

    event_list: List[TksComedyEvent]
