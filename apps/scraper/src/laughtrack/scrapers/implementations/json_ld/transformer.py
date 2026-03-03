"""
JSON-LD data transformation utilities.

This module provides utilities for transforming Event objects
into Show objects, implementing the DataTransformer interface.
"""

from laughtrack.utilities.infrastructure.transformer.base import DataTransformer
from laughtrack.core.entities.event.event import JsonLdEvent


class JsonLdTransformer(DataTransformer[JsonLdEvent]):
    pass
