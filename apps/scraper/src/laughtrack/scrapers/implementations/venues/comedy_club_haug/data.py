"""Data model for scraped page data from Comedy Club Haug."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.comedy_club_haug import ComedyClubHaugEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class ComedyClubHaugPageData(EventListContainer[ComedyClubHaugEvent]):
    """Raw extracted event data from Comedy Club Haug."""

    event_list: List[ComedyClubHaugEvent]
