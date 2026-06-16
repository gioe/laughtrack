"""Data model for scraped page data from The Auricle."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.the_auricle import TheAuricleEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TheAuriclePageData(EventListContainer[TheAuricleEvent]):
    """Container for TheAuricleEvent objects extracted from the accentapi feed."""

    event_list: List[TheAuricleEvent]
