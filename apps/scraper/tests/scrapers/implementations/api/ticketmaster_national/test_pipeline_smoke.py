"""
Pipeline smoke tests for TicketmasterNationalScraper.

Exercises the scrape_async() override:
  _fetch_national_comedy_events() -> _process_events() -> List[Show]

Key assertions:
- collect_scraping_targets() returns ["national"]
- scrape_async() returns Shows when national comedy events are available
- scrape_async() returns [] when no events are returned by the Discovery API
"""

import importlib.util
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.show.model import Show
from laughtrack.scrapers.implementations.api.ticketmaster_national.scraper import (
    TicketmasterNationalScraper,
)


def _club() -> Club:
    """Minimal platform club row that triggers the national scraper."""
    _c = Club(id=999, name='Ticketmaster National', address='', website='', popularity=0, zip_code='', phone_number='', visible=True)
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='ticketmaster_national', scraper_key='ticketmaster_national', source_url='www.ticketmaster.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _make_show(name: str = "Comedy Night") -> Show:
    """Minimal Show object for mocked _process_events results."""
    from datetime import datetime, timezone

    return Show(
        name=name,
        club_id=1,
        date=datetime(2026, 6, 15, 20, 0, tzinfo=timezone.utc),
        show_page_url="https://www.ticketmaster.com/event/0200638B27F56222",
        timezone="America/Chicago",
    )


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_national():
    """collect_scraping_targets() returns a single ["national"] target."""
    scraper = TicketmasterNationalScraper(_club())
    targets = await scraper.collect_scraping_targets()
    assert targets == ["national"]


@pytest.mark.asyncio
async def test_scrape_async_returns_shows_when_events_exist():
    """
    scrape_async() produces Shows when _fetch_national_comedy_events returns
    events and _process_events converts them successfully.
    """
    scraper = TicketmasterNationalScraper(_club())
    expected_shows = [_make_show("Chris Redd Live"), _make_show("Taylor Tomlinson Tour")]

    with (
        patch.object(
            scraper,
            "_fetch_national_comedy_events",
            new=AsyncMock(return_value=[object(), object()]),  # 2 raw API events
        ),
        patch.object(
            scraper,
            "_process_events",
            new=AsyncMock(return_value=expected_shows),
        ),
    ):
        shows = await scraper.scrape_async()

    assert len(shows) == 2, (
        "scrape_async() should return 2 Shows when _process_events returns 2"
    )
    assert all(isinstance(s, Show) for s in shows)


@pytest.mark.asyncio
async def test_scrape_async_returns_empty_when_no_events():
    """
    scrape_async() returns [] when _fetch_national_comedy_events returns
    an empty list (no comedy events from the Ticketmaster Discovery API).
    """
    scraper = TicketmasterNationalScraper(_club())

    with patch.object(
        scraper,
        "_fetch_national_comedy_events",
        new=AsyncMock(return_value=[]),
    ):
        shows = await scraper.scrape_async()

    assert shows == [], (
        "scrape_async() should return [] when no national events are found"
    )
