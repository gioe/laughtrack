"""Data model for AXS-skinned venue homepage scraped data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.axs import AXSEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class AXSPageData(EventListContainer[AXSEvent]):
    """Container for events extracted from an AXS-skinned venue homepage."""

    event_list: List[AXSEvent]
