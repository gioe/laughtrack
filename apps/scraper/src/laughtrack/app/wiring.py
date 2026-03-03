"""Simple wiring for adapters and configuration.

This keeps the rest of the code from importing concrete implementations directly.
We can evolve this toward dependency injection later without changing call sites.
"""

from dataclasses import dataclass

from laughtrack.adapters.config import ConfigManager, ScraperMapping
from laughtrack.adapters.http import http_client
from laughtrack.adapters.db import db
from laughtrack.ports.http import HttpClientProtocol
from laughtrack.ports.database import DatabaseConnection
from laughtrack.app.scraper_resolver import ScraperResolver


@dataclass
class Services:
    config: type[ConfigManager]
    scraper_mapping: ScraperMapping
    http_client: HttpClientProtocol
    db: DatabaseConnection
    scraper_resolver: ScraperResolver


def build_services() -> Services:
    """Construct adapter services for app/usecases and commands."""
    return Services(
        config=ConfigManager,
        scraper_mapping=ScraperMapping(),
    http_client=http_client,
    db=db,
    scraper_resolver=ScraperResolver(),
    )
