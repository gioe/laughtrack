"""Page data container for the generic OvationTix platform scraper."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.ovationtix import OvationTixEvent


@dataclass
class OvationTixPageData:
    """Container for OvationTix performances extracted from the API."""

    event_list: List[OvationTixEvent]

    def has_data(self) -> bool:
        return bool(self.event_list)
