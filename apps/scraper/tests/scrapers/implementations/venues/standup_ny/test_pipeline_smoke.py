"""
Pipeline smoke test for StandUp NY scraper.

StandUp NY uses a custom two-phase workflow:
  1. discover_urls() — GraphQL discovery, sets self.page_data, returns VenuePilot URLs
  2. get_data(url) — VenuePilot ticket enhancement per event

Both phases are exercised against fixture data by mocking the extractor.
"""

import importlib.util
from typing import Optional
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.standup_ny import StandupNYEvent
from laughtrack.scrapers.implementations.venues.standup_ny.scraper import StandupNYScraper
from laughtrack.scrapers.implementations.venues.standup_ny.data import StandupNYPageData


VENUEPILOT_URL = "https://tickets.venuepilot.com/e/standup-night-1"


def _club() -> Club:
    _c = Club(id=99, name='StandUp NY', address='', website='https://standupny.com', popularity=0, zip_code='', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://api.showtix4u.com/graphql', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _fake_event() -> StandupNYEvent:
    return StandupNYEvent(
        id="sny-evt-1",
        name="StandUp NY Comedy Night",
        date="2026-04-15",
        start_time="20:00",
        ticket_url=VENUEPILOT_URL,
        promoter="Test Comedian",
    )


def _fake_page_data() -> StandupNYPageData:
    return StandupNYPageData(event_list=[_fake_event()])


@pytest.mark.asyncio
async def test_discover_urls_returns_venuepilot_urls(monkeypatch):
    """discover_urls() returns VenuePilot ticket URLs from GraphQL-discovered events."""
    scraper = StandupNYScraper(_club())

    monkeypatch.setattr(
        scraper.extractor,
        "extract_events",
        AsyncMock(return_value=_fake_page_data()),
    )

    urls = await scraper.discover_urls()
    assert len(urls) > 0, (
        "discover_urls() returned 0 VenuePilot URLs — "
        "check extractor.extract_events() mock returned a StandupNYPageData with a venuepilot ticket_url"
    )
    assert urls[0] == VENUEPILOT_URL


@pytest.mark.asyncio
async def test_get_data_returns_enhanced_event(monkeypatch):
    """get_data() returns enhanced event dict when VenuePilot enhancement succeeds."""
    scraper = StandupNYScraper(_club())

    # Pre-populate page_data (normally set by discover_urls)
    scraper.page_data = _fake_page_data()

    monkeypatch.setattr(
        scraper.extractor,
        "enhance_event_with_venue_pilot",
        AsyncMock(return_value=True),
    )

    result = await scraper.get_data(VENUEPILOT_URL)

    assert result is not None, "get_data() returned None for a matching VenuePilot URL"
    assert "enhanced_event" in result, "get_data() result missing 'enhanced_event' key"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: discover_urls() → get_data() produces enhanced event data."""
    scraper = StandupNYScraper(_club())

    monkeypatch.setattr(
        scraper.extractor,
        "extract_events",
        AsyncMock(return_value=_fake_page_data()),
    )
    monkeypatch.setattr(
        scraper.extractor,
        "enhance_event_with_venue_pilot",
        AsyncMock(return_value=True),
    )

    urls = await scraper.discover_urls()
    assert len(urls) > 0, "discover_urls() returned 0 URLs"

    enhanced_results = []
    for url in urls:
        result = await scraper.get_data(url)
        if result:
            enhanced_results.append(result)

    assert len(enhanced_results) > 0, "Full pipeline produced 0 enhanced event results"
