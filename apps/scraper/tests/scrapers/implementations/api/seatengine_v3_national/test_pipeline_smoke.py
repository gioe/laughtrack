"""
Pipeline smoke tests for SeatEngineV3NationalScraper.

Verifies that collect_scraping_targets(), get_data(), and scrape_async()
wire together correctly for the v3 national discovery scraper.

SeatEngineV3NationalScraper overrides scrape_async() — it discovers UUID-based
venues via the Wayback Machine CDX API and v3 GraphQL, upserts club rows, and
returns an empty show list.  get_data() is not used (returns None).
"""

import importlib.util
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.api.seatengine_v3_national.scraper import SeatEngineV3NationalScraper


_UUID_A = "cf2b1561-bf36-40b8-8380-9c2a3bd0e4e3"
_UUID_B = "e7ea1e53-8a31-48b6-bfe4-fd9672791615"


def _platform_club() -> Club:
    _c = Club(id=999, name='SeatEngine V3 National', address='', website='', popularity=0, zip_code='', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='seatengine_v3_national', scraper_key='seatengine_v3_national', source_url='www.seatengine.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _venue_dict(uuid: str = _UUID_A, name: str = "The Comedy Studio") -> dict:
    return {
        "uuid": uuid,
        "name": name,
        "website": "https://thecomedystudio.com",
        "address": "5 John F. Kennedy St",
        "city": "Cambridge",
        "state": "MA",
        "zipCode": "02138",
    }


def _upserted_club(uuid: str = _UUID_A) -> Club:
    _c = Club(id=1, name='The Comedy Studio', address='5 John F. Kennedy St', website='https://thecomedystudio.com', popularity=0, zip_code='02138', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='seatengine_v3', scraper_key='seatengine_v3', source_url=f'https://v-{uuid}.seatengine.net', external_id=uuid)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


# ---------------------------------------------------------------------------
# collect_scraping_targets()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_national():
    """collect_scraping_targets() returns the single logical 'national' target."""
    scraper = SeatEngineV3NationalScraper(_platform_club())
    targets = await scraper.collect_scraping_targets()
    assert targets == ["national"]


# ---------------------------------------------------------------------------
# get_data() — not used in this scraper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_data_returns_none():
    """get_data() returns None — scrape_async() drives the full pipeline."""
    scraper = SeatEngineV3NationalScraper(_platform_club())
    result = await scraper.get_data("national")
    assert result is None


# ---------------------------------------------------------------------------
# scrape_async() — discovers venues, upserts clubs, returns no shows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scrape_async_returns_no_shows_when_venues_found():
    """scrape_async() upserts discovered venues and returns [] (discovery only)."""
    scraper = SeatEngineV3NationalScraper(_platform_club())
    venues = [_venue_dict(_UUID_A), _venue_dict(_UUID_B, name="Cafe Coda")]
    club = _upserted_club()

    with patch.object(scraper, "_fetch_v3_venues", new=AsyncMock(return_value=venues)):
        with patch.object(
            scraper._club_handler,
            "upsert_for_seatengine_v3_venue",
            return_value=club,
        ) as mock_upsert:
            shows = await scraper.scrape_async()

    assert shows == []
    assert mock_upsert.call_count == 2


@pytest.mark.asyncio
async def test_scrape_async_returns_empty_when_no_venues():
    """scrape_async() returns [] when CDX discovery yields no venues."""
    scraper = SeatEngineV3NationalScraper(_platform_club())

    with patch.object(scraper, "_fetch_v3_venues", new=AsyncMock(return_value=[])):
        shows = await scraper.scrape_async()

    assert shows == []
