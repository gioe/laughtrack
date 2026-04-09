"""Data model for scraped page data from Laffs Comedy Cafe."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.laffs_comedy_cafe import LaffsComedyCafeEvent


@dataclass
class LaffsComedyCafePageData:
    """Raw extracted event data from the Laffs Comedy Cafe coming-soon page."""

    event_list: List[LaffsComedyCafeEvent]
