"""Unit tests for ShopifyScraper — default_show_time metadata parsing (TASK-3378)."""

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.american_comedy_co.scraper import (
    ShopifyScraper,
)


def _scraper(default_show_time=None) -> ShopifyScraper:
    metadata = {}
    if default_show_time is not None:
        metadata["default_show_time"] = default_show_time
    club = Club(
        id=1,
        name="Kesha's Comedy House",
        address="20958 Gratiot Ave",
        website="https://keshascomedyhouse.com",
        popularity=0,
        zip_code="48021",
        phone_number="",
        visible=True,
        timezone="America/Detroit",
    )
    club.active_scraping_source = ScrapingSource(
        id=1,
        club_id=club.id,
        platform="custom",
        scraper_key="shopify",
        source_url="https://keshascomedyhouse.com",
        metadata=metadata,
    )
    club.scraping_sources = [club.active_scraping_source]
    return ShopifyScraper(club)


def test_default_time_none_when_metadata_absent():
    assert _scraper()._default_time() is None


def test_default_time_parses_24h_hhmm():
    assert _scraper("20:00")._default_time() == (20, 0)
    assert _scraper("19:30")._default_time() == (19, 30)


def test_default_time_parses_clock_string():
    assert _scraper("8pm")._default_time() == (20, 0)
    assert _scraper("7:30 PM")._default_time() == (19, 30)


def test_default_time_invalid_returns_none():
    assert _scraper("not-a-time")._default_time() is None
    assert _scraper("25:00")._default_time() is None
    assert _scraper("")._default_time() is None
