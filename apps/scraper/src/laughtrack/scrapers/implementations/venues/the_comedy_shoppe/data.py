"""Data model for scraped page data from a ShowSlinger widget."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.show_slinger import ShowSlingerEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ShowSlingerPageData(EventListContainer[ShowSlingerEvent]):
    """Raw extracted data from a ShowSlinger combo widget."""

    event_list: List[ShowSlingerEvent]


@dataclass
class ShoppePageData(EventListContainer):
    """Reviewed PunchUp occurrences ready for the conversion pipeline."""

    event_list: list
