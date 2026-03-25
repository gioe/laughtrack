"""Data model for scraped page data from Dynasty Typewriter."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.dynasty_typewriter import DynastyTypewriterEvent


@dataclass
class DynastyTypewriterPageData:
    """Raw extracted event data from Dynasty Typewriter's SquadUp API."""

    event_list: List[DynastyTypewriterEvent]
