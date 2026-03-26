"""
Pipeline smoke tests for SeatEngineNationalScraper.

Verifies that collect_scraping_targets(), get_data(), and scrape_async()
wire together correctly for the national enumeration scraper.

SeatEngineNationalScraper overrides scrape_async() — it discovers venues
by scanning numeric IDs 1…N concurrently, upserts club rows, and returns
an empty show list.  get_data() is not used (returns None).
"""

import importlib.util
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club
from laughtrack.scrapers.implementations.api.seatengine_national.scraper import SeatEngineNationalScraper


def _platform_club() -> Club:
    return Club(
        id=999,
        name="SeatEngine National",
        address="",
        website="",
        scraping_url="www.seatengine.com",
        popularity=0,
        zip_code="",
        phone_number="",
        visible=True,
        scraper="seatengine_national",
    )


def _venue_dict(venue_id: int = 42, name: str = "Joe's Comedy Club") -> dict:
    return {"id": venue_id, "name": name, "address": "123 Main St", "zip": "10001", "website": ""}


def _upserted_club(seatengine_id: str = "42") -> Club:
    return Club(
        id=1,
        name="Joe's Comedy Club",
        address="123 Main St",
        website="",
        scraping_url="www.seatengine.com",
        popularity=0,
        zip_code="10001",
        phone_number="",
        visible=True,
        scraper="seatengine",
        seatengine_id=seatengine_id,
    )


def _make_scraper() -> SeatEngineNationalScraper:
    with patch(
        "laughtrack.scrapers.implementations.api.seatengine_national.scraper.ConfigManager.get_config",
        return_value="fake_token",
    ):
        return SeatEngineNationalScraper(_platform_club())


# ---------------------------------------------------------------------------
# collect_scraping_targets()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_national():
    """collect_scraping_targets() returns the single logical 'national' target."""
    scraper = _make_scraper()
    targets = await scraper.collect_scraping_targets()
    assert targets == ["national"]


# ---------------------------------------------------------------------------
# get_data() — not used in this scraper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_none():
    """get_data() returns None — scrape_async() drives the full pipeline."""
    scraper = _make_scraper()
    result = await scraper.get_data("national")
    assert result is None


# ---------------------------------------------------------------------------
# scrape_async() — discovers venues, upserts clubs, returns no shows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scrape_async_returns_no_shows_when_venues_found():
    """scrape_async() upserts discovered venues and returns [] (enumeration only)."""
    scraper = _make_scraper()
    venues = [_venue_dict(42), _venue_dict(43, name="Brokerage Comedy Club")]
    club = _upserted_club()

    with patch.object(scraper, "_fetch_seatengine_venues", new=AsyncMock(return_value=venues)):
        with patch.object(
            scraper._club_handler,
            "upsert_for_seatengine_venue",
            return_value=club,
        ) as mock_upsert:
            shows = await scraper.scrape_async()

    assert shows == []
    assert mock_upsert.call_count == 2


@pytest.mark.asyncio
async def test_scrape_async_returns_empty_when_no_venues():
    """scrape_async() returns [] when the ID scan yields no venues."""
    scraper = _make_scraper()

    with patch.object(scraper, "_fetch_seatengine_venues", new=AsyncMock(return_value=[])):
        shows = await scraper.scrape_async()

    assert shows == []
