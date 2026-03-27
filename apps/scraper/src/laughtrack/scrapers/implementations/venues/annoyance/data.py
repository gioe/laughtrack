"""Page data model for The Annoyance Theatre scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.annoyance import AnnoyancePerformance
from laughtrack.ports.scraping import EventListContainer


@dataclass
class AnnoyancePageData(EventListContainer[AnnoyancePerformance]):
    """Raw extracted data from The Annoyance Theatre ThunderTix calendar API."""

    event_list: List[AnnoyancePerformance]
