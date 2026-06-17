"""Data model for AXS-skinned venue homepage scraped data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.axs import AXSEvent


@dataclass
class AXSPageData:
    """Container for events extracted from an AXS-skinned venue homepage."""

    event_list: List[AXSEvent]
