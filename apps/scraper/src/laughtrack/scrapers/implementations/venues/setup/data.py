"""Data model for scraped page data from The Setup."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.setup import SetupEvent


@dataclass
class SetupPageData:
    """Raw extracted event data from The Setup's Google Sheets CSV."""

    event_list: List[SetupEvent]
