"""Page data model for Newport Comedy Series scraper."""

from dataclasses import dataclass
from typing import List

from .extractor import NewportComedySeriesShow


@dataclass
class NewportComedySeriesPageData:
    """
    Container for show data extracted from Newport Comedy Series' Punchup page.

    Implements the EventListContainer protocol required by BaseScraper.
    """

    event_list: List[NewportComedySeriesShow]
