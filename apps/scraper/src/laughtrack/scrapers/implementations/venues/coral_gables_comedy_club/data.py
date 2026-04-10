"""Data model for scraped page data from Coral Gables Comedy Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.coral_gables_comedy_club import (
    CoralGablesComedyClubEvent,
)
from laughtrack.ports.scraping import EventListContainer


@dataclass
class CoralGablesComedyClubPageData(
    EventListContainer[CoralGablesComedyClubEvent]
):
    """Container for events extracted from the Square Online products API."""

    event_list: List[CoralGablesComedyClubEvent]
