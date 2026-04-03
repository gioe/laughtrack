"""
Extractor helpers for Ticketmaster API responses.
"""

from typing import List

from laughtrack.foundation.models.types import JSONDict


class TicketmasterExtractor:
    @staticmethod
    def to_page_data(events: List[JSONDict]):
        from .data import TicketmasterPageData

        return TicketmasterPageData(event_list=events)
