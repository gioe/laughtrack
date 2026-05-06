"""Page data model for LAUGH IT UP COMEDY CLUB scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.clients.punchup.extractor import PunchupShow


@dataclass
class LaughItUpComedyShow(PunchupShow):
    """A show parsed from LAUGH IT UP COMEDY CLUB's Punchup page."""


@dataclass
class LaughItUpComedyPageData:
    """
    Container for show data extracted from LAUGH IT UP COMEDY CLUB's Punchup page.

    Implements the EventListContainer protocol required by BaseScraper.
    """

    event_list: List[LaughItUpComedyShow]
