"""Data model for Pabst Theater Group venue-page scraped data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.pabst_axs import PabstAXSEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class PabstAXSPageData(EventListContainer[PabstAXSEvent]):
    """Container for events extracted from a Pabst Theater Group venue page."""

    event_list: List[PabstAXSEvent]
