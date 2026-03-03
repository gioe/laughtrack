"""
Bushwick Comedy Club data transformation utilities.

This module provides utilities for transforming BushwickEvent objects
into Show objects, implementing the DataTransformer interface.
"""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer

from .extractor import BushwickEvent


class BushwickEventTransformer(DataTransformer[BushwickEvent]):
    pass
