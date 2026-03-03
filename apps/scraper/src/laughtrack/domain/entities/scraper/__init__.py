"""Domain scraper entity facade.

Provides a stable import path for scraper-related services from the domain layer.
"""

from .service import ScraperService  # noqa: F401

__all__ = ["ScraperService"]
