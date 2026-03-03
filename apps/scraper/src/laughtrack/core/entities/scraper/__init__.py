"""
User entity - colocated model and handler.
"""

from .handler import ScraperHandler
from .model import Scraper
from .service  import ScraperService

__all__ = ["Scraper", "ScraperHandler", "ScraperService"]
