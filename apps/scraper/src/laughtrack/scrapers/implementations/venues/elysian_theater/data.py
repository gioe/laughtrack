"""Data model for scraped page data from The Elysian Theater."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.elysian import ElysianEvent


@dataclass
class ElysianPageData:
    """Raw extracted event data from The Elysian Theater's Squarespace API."""

    event_list: List[ElysianEvent]
