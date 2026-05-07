"""Page data for Dr. Grins Comedy Club public pages."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.dr_grins import DrGrinsEvent


@dataclass
class DrGrinsPageData:
    """Raw extracted performances from one Dr. Grins comedian detail page."""

    event_list: List[DrGrinsEvent]
