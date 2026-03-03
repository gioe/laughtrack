"""Domain wrapper for ScraperService.

This allows external code to import the scraper service from the domain layer,
while the implementation is sourced from the current core location during migration.
"""

from laughtrack.core.entities.scraper.service import ScraperService  # re-export

__all__ = ["ScraperService"]
