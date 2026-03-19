"""Page data model for Comedy Key West scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.clients.punchup.extractor import PunchupShow


@dataclass
class ComedyKeyWestPageData:
    """
    Container for show data extracted from Comedy Key West's Punchup page.

    Implements the EventListContainer protocol required by BaseScraper.
    """

    event_list: List[PunchupShow]
