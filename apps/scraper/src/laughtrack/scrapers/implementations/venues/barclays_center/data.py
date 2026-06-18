"""Page data for Barclays Center comedy category pages."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.barclays_center import BarclaysCenterEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class BarclaysCenterPageData(EventListContainer[BarclaysCenterEvent]):
    """Raw extracted Barclays Center comedy events."""

    event_list: List[BarclaysCenterEvent]
