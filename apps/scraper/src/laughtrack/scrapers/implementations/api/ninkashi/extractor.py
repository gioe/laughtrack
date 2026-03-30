"""Ninkashi event extractor."""

from typing import List

from laughtrack.core.entities.event.ninkashi import NinkashiEvent

from .data import NinkashiPageData


class NinkashiExtractor:
    """Converts a raw Ninkashi API response list into a NinkashiPageData."""

    @staticmethod
    def to_page_data(events: List[NinkashiEvent]) -> NinkashiPageData:
        return NinkashiPageData(event_list=events)
