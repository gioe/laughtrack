"""
Data model for scraped page data from Bushwick Comedy Club.
"""

from dataclasses import dataclass
from typing import List

from .extractor import BushwickEvent


@dataclass
class BushwickEventData:
    """
    Data model representing raw extracted data from a scraped webpage/API response.

    This contains the BushwickEvent objects extracted from Bushwick Comedy Club's
    Wix API response, following the standard PageData pattern.
    """

    event_list: List[BushwickEvent]
