"""
Domain-specific utilities for Laughtrack entities.

These utilities depend on Laughtrack domain models (Show, Comedian, Club, etc.)
and contain business logic specific to the comedy show domain.
"""

from .utils import TagUtils

__all__ = [
    "TagUtils",
]
