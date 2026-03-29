"""Data model for scraped page data from The Comedy Corner Underground."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.comedy_corner_underground import ComedyCornerEvent


@dataclass
class ComedyCornerPageData:
    """Raw extracted event data from The Comedy Corner Underground StageTime pages."""

    event_list: List[ComedyCornerEvent]
