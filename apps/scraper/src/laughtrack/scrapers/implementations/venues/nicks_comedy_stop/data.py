from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.nicks import NicksEvent


@dataclass
class NicksPageData:
    """Raw extracted event data from Nick's Comedy Stop's Wix Events API."""

    event_list: List[NicksEvent]
