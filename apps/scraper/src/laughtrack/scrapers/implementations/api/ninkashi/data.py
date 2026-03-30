"""Data model for scraped page data from a Ninkashi-powered venue."""

from dataclasses import dataclass
from typing import List

from laughtrack.core.entities.event.ninkashi import NinkashiEvent


@dataclass
class NinkashiPageData:
    """Raw event data fetched from the Ninkashi public API."""

    event_list: List[NinkashiEvent]
