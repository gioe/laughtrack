"""Data model for scraped page data from Comedy Club Haug."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.comedy_club_haug import ComedyClubHaugEvent


@dataclass
class ComedyClubHaugPageData:
    """Raw extracted event data from Comedy Club Haug."""

    event_list: List[ComedyClubHaugEvent]
