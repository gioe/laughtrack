"""Page data model for Side Splitters Comedy Club scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.clients.punchup.extractor import PunchupShow
from laughtrack.ports.scraping import EventListContainer


@dataclass
class SideSplittersShow(PunchupShow):
    """A show parsed from Side Splitters' Punchup page."""


@dataclass
class SideSplittersPageData(EventListContainer[SideSplittersShow]):
    """Container for show data extracted from Side Splitters' Punchup page."""

    event_list: List[SideSplittersShow]
