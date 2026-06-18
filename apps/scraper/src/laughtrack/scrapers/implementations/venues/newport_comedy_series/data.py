"""Page data model for Newport Comedy Series scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.ports.scraping import EventListContainer
from .extractor import NewportComedySeriesShow


@dataclass
class NewportComedySeriesPageData(EventListContainer[NewportComedySeriesShow]):
    """
    Container for show data extracted from Newport Comedy Series' Punchup page.

    Implements the EventListContainer protocol required by BaseScraper.
    """

    event_list: List[NewportComedySeriesShow]
