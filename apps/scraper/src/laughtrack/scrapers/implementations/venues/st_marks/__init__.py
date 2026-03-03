"""
St. Marks Comedy Club scraper implementation.

This module implements the 5-component architecture for St. Marks Comedy Club:
- StMarksScraper: Main orchestration class
- StMarksEventExtractor: Data extraction utilities
- StMarksEventTransformer: Data transformation to Show objects
- StMarksPageData: Data model for extracted page data
- TixrEvent: Domain model for Tixr-specific event data (in core.models)
"""

from .data import StMarksPageData
from .extractor import StMarksEventExtractor
from .transformer import StMarksEventTransformer

__all__ = [
    "StMarksEventExtractor",
    "StMarksEventTransformer",
    "StMarksPageData",
]
