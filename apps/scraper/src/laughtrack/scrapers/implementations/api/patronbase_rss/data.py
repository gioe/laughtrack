"""Data container for PatronBase RSS events."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.patronbase_rss import PatronBaseRssEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class PatronBaseRssPageData(EventListContainer[PatronBaseRssEvent]):
    """Container for events parsed from a PatronBase RSS feed."""

    event_list: List[PatronBaseRssEvent]
