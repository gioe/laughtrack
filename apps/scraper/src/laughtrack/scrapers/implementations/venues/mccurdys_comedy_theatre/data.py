"""Data model for scraped page data from McCurdy's Comedy Theatre."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.mccurdys_comedy_theatre import McCurdysEvent


@dataclass
class McCurdysPageData:
    """Raw extracted event data from a McCurdy's Comedy Theatre detail page."""

    event_list: List[McCurdysEvent]
