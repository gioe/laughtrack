"""
Extractor helpers for SeatEngine API responses.
"""

from typing import List

from laughtrack.foundation.models.types import JSONDict


class SeatEngineExtractor:
    @staticmethod
    def to_page_data(events: List[JSONDict]):
        from .page_data import SeatEnginePageData

        return SeatEnginePageData(event_list=events)
