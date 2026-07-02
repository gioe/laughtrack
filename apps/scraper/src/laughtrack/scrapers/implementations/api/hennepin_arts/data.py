"""Page data for Hennepin Arts events."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.hennepin_arts import HennepinArtsEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class HennepinArtsPageData(EventListContainer[HennepinArtsEvent]):
    """Container for Hennepin Arts event data."""

    event_list: List[HennepinArtsEvent]
