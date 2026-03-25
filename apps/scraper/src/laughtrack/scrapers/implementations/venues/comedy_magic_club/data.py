"""Data model for scraped page data from The Comedy & Magic Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.comedy_magic_club import ComedyMagicClubEvent


@dataclass
class ComedyMagicClubPageData:
    """Raw extracted event data from The Comedy & Magic Club listing page."""

    event_list: List[ComedyMagicClubEvent]
