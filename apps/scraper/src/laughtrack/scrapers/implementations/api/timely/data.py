"""Data model for Timely API page data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.timely import TimelyEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class TimelyPageData(EventListContainer[TimelyEvent]):
    """Raw extracted event data from a Timely calendar API response."""

    event_list: List[TimelyEvent]

