"""Data model for scraped page data from Dr. Grins Comedy Club."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.dr_grins import DrGrinsEvent


@dataclass
class DrGrinsPageData:
    """Raw extracted event data from the Etix venue page."""

    event_list: List[DrGrinsEvent]
