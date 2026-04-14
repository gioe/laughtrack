"""Event extraction for Brew HaHa Comedy at River.

The Comedy Craft Beer calendar (comedycraftbeer.com/calendar) embeds JSON-LD
for ALL venues. This extractor reuses the generic JSON-LD parser and filters
to events at the River venue only.
"""

from typing import List

from laughtrack.core.entities.event.event import JsonLdEvent
from laughtrack.scrapers.implementations.json_ld.extractor import EventExtractor


RIVER_VENUE_NAME = "River: A Waterfront Restaurant and Bar"


class BrewHaHaRiverExtractor:
    """Extract JSON-LD events filtered to the River venue."""

    @staticmethod
    def extract_events(html: str) -> List[JsonLdEvent]:
        all_events = EventExtractor.extract_events(html)
        return [
            e for e in all_events
            if e.location and RIVER_VENUE_NAME in e.location.name
        ]
