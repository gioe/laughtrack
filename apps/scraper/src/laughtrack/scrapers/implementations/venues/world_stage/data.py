"""Page data container for the World Stage scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.world_stage import WorldStageEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class WorldStagePageData(EventListContainer[WorldStageEvent]):
    """Confirmed events extracted from the World Stage Ciright calendar."""

    event_list: List[WorldStageEvent]
