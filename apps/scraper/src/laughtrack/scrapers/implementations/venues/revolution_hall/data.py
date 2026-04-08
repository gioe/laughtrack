"""Data model for scraped page data from Revolution Hall."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.revolution_hall import RevolutionHallEvent


@dataclass
class RevolutionHallPageData:
    """Container for all events extracted from the Revolution Hall homepage."""

    event_list: List[RevolutionHallEvent]
