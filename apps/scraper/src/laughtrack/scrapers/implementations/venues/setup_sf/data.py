"""Data model for scraped page data from The Setup SF."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.setup_sf import SetupSFEvent


@dataclass
class SetupSFPageData:
    """Raw extracted event data from The Setup SF's Google Sheets CSV."""

    event_list: List[SetupSFEvent]
