"""Data model for scraped page data from a Squarespace-powered venue."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.squarespace import SquarespaceEvent


@dataclass
class SquarespacePageData:
    """Raw extracted event data from a Squarespace venue's GetItemsByMonth API."""

    event_list: List[SquarespaceEvent]
