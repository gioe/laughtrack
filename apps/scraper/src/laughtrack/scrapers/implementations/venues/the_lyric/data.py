"""Page data container for the Indy Systems (The Lyric) scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.ports.scraping import EventListContainer
from laughtrack.scrapers.implementations.venues.the_lyric.event import TheLyricEvent


@dataclass
class TheLyricPageData(EventListContainer[TheLyricEvent]):
    """Comedy showings extracted from the Indy Systems GraphQL proxy."""

    event_list: List[TheLyricEvent]
