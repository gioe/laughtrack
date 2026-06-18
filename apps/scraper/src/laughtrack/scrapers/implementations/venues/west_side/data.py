"""Page data model for West Side Comedy Club scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.ports.scraping import EventListContainer
from .extractor import WestSideShow


@dataclass
class WestSidePageData(EventListContainer[WestSideShow]):
    """
    Container for show data extracted from West Side Comedy Club's Punchup page.

    Implements the EventListContainer protocol required by BaseScraper.
    """

    event_list: List[WestSideShow]
