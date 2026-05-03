"""Page data model for Palm Beach Improv at the Kravis Center."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.palm_beach_improv import PalmBeachImprovEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class PalmBeachImprovPageData(EventListContainer[PalmBeachImprovEvent]):
    """Raw Palm Beach Improv events extracted from one Kravis calendar month."""

    event_list: List[PalmBeachImprovEvent]
