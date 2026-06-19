"""Page data for Kenosha Comedy Club WordPress posts."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.kenosha_comedy_club import KenoshaComedyClubEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class KenoshaComedyClubPageData(EventListContainer[KenoshaComedyClubEvent]):
    """Raw extracted Kenosha Comedy Club events."""

    event_list: List[KenoshaComedyClubEvent]
