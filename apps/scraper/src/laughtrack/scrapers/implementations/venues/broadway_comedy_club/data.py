"""
Data model for scraped page data from Broadway Comedy Club.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.broadway import BroadwayEvent



@dataclass
class BroadwayEventData:
    event_list: List[BroadwayEvent]
