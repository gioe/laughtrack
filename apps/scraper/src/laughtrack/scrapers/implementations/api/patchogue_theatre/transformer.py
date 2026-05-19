"""Transformer for the Patchogue Theatre scraper.

Re-exports the shared :class:`OvationTixEventTransformer` — Patchogue events
are :class:`OvationTixEvent` instances and need no venue-specific override.
"""

from laughtrack.scrapers.implementations.api.ovationtix.transformer import (
    OvationTixEventTransformer,
)

__all__ = ["OvationTixEventTransformer"]
