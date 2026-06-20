"""Data container for the TicketsCandy scraper.

TicketsCandy event pages carry standard schema.org Event JSON-LD, so events are
parsed into the shared ``JsonLdEvent`` model (reusing the json_ld extractor /
transformer). This container just bundles them for the BaseScraper pipeline.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TicketsCandyPageData(EventListContainer[JsonLdEvent]):
    """Holds the JsonLdEvent objects parsed from one TicketsCandy event page."""

    event_list: List[JsonLdEvent]
