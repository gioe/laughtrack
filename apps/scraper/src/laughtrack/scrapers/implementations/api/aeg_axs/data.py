"""Data model for AEG/Goldenvoice Carbonhouse venue-page scraped data."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.aeg_axs import AEGAXSEvent
from laughtrack.ports.scraping import EventListContainer


@dataclass
class AEGAXSPageData(EventListContainer[AEGAXSEvent]):
    """Container for events extracted from an AEG Carbonhouse ``/events`` page."""

    event_list: List[AEGAXSEvent]
