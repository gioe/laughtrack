"""Page data for Rumor's Comedy Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.rumors_comedy_club import RumorsComedyClubEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class RumorsComedyClubPageData(EventListContainer[RumorsComedyClubEvent]):
    """Raw extracted Rumor's Comedy Club events."""

    event_list: List[RumorsComedyClubEvent]
