"""
Page data facade for Eventbrite API scrapers.

This re-exports the concrete data model from data.py so other modules
should import from .page_data to satisfy the 5-file structure.
"""

from .data import EventbriteVenueData  # noqa: F401
