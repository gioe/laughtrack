"""Page data for Barclays Center comedy category pages."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.barclays_center import BarclaysCenterEvent


@dataclass
class BarclaysCenterPageData:
    """Raw extracted Barclays Center comedy events."""

    event_list: List[BarclaysCenterEvent]
