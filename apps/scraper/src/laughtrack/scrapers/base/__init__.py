"""Base scraper classes and utilities."""

from .base_scraper import BaseScraper
from .email_base_scraper import EmailBaseScraper
from .email_page_data import EmailPageData

__all__ = ["BaseScraper", "EmailBaseScraper", "EmailPageData"]
