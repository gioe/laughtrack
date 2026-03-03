"""Rodney's Comedy Club package.

Exports data/extractor/transformer only to avoid import-time cycles. The
scraper class is discovered dynamically by the registry when needed.
"""

from .data import RodneyPageData
from .extractor import RodneyEventExtractor
from .transformer import RodneyEventTransformer

__all__ = [
    "RodneyEventExtractor",
    "RodneyEventTransformer",
    "RodneyPageData",
]
