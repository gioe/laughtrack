"""Data model for scraped UP Comedy Club Second City platform response."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.up_comedy_club import UPComedyClubEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class UPComedyClubPageData(EventListContainer[UPComedyClubEvent]):
    """Raw extracted data from the Second City platform (one entry per performance)."""

    event_list: List[UPComedyClubEvent]
