"""Page data for the Coral Springs Center for the Arts venue scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.coral_springs_center import (
    CoralSpringsCenterEvent,
)
from laughtrack.ports.scraping import EventListContainer


@dataclass
class CoralSpringsCenterPageData(EventListContainer[CoralSpringsCenterEvent]):
    """Container for comedy events extracted from the venue's own site."""

    event_list: List[CoralSpringsCenterEvent]
