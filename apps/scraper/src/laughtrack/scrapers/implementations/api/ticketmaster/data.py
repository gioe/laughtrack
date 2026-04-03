"""
Page data model for Ticketmaster API results.

This minimal container implements the EventListContainer protocol.
"""

from dataclasses import dataclass
from typing import List

from laughtrack.foundation.models.types import JSONDict


@dataclass
class TicketmasterPageData:
    event_list: List[JSONDict]

    def is_transformable(self) -> bool:
        return bool(self.event_list)
