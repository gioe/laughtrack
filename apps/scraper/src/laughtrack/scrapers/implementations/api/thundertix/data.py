"""Page data model for the generic ThunderTix calendar API scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.thundertix import ThunderTixPerformance
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ThunderTixPageData(EventListContainer[ThunderTixPerformance]):
    """Raw extracted data from a ThunderTix calendar API window."""

    event_list: List[ThunderTixPerformance]
