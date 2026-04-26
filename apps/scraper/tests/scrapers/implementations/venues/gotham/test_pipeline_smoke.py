"""
Pipeline smoke test for Gotham Comedy Club scraper.

Exercises collect_scraping_targets() (pure date generation) → get_data()
by mocking GothamEventExtractor.extract_events to return a fixture GothamPageData.
"""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.gotham import GothamEvent
from laughtrack.scrapers.implementations.venues.gotham.scraper import GothamComedyClubScraper
from laughtrack.scrapers.implementations.venues.gotham.data import GothamPageData
from laughtrack.scrapers.implementations.venues.gotham.extractor import GothamEventExtractor


def _club() -> Club:
    _c = Club(id=99, name='Gotham Comedy Club', address='', website='https://www.gothamcomedyclub.com', popularity=0, zip_code='', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://www.gothamcomedyclub.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _fake_gotham_event() -> GothamEvent:
    return GothamEvent(
        id="gotham-evt-1",
        name="Gotham Showcase",
        date="2026-04-15",
        hours=20,
        minutes=0,
        slug="gotham-showcase",
        shows=[],
    )


@pytest.mark.asyncio
async def test_collect_scraping_targets_generates_monthly_urls():
    """collect_scraping_targets() generates S3 monthly JSON URLs (no HTTP calls)."""
    scraper = GothamComedyClubScraper(_club())
    urls = await scraper.collect_scraping_targets()
    assert len(urls) >= 1, "collect_scraping_targets() returned 0 URLs"
    assert all("gothamevents.s3.amazonaws.com" in u for u in urls), (
        f"Expected S3 URLs, got: {urls[:3]}"
    )
    assert all(u.endswith(".json") for u in urls), "Expected .json-suffixed monthly URLs"


@pytest.mark.asyncio
async def test_get_data_returns_events_from_extractor(monkeypatch):
    """get_data() returns GothamPageData when extractor.extract_events() yields events."""
    scraper = GothamComedyClubScraper(_club())
    fake_page_data = GothamPageData(event_list=[_fake_gotham_event()])

    monkeypatch.setattr(
        scraper.extractor,
        "extract_events",
        AsyncMock(return_value=fake_page_data),
    )

    result = await scraper.get_data("https://gothamevents.s3.amazonaws.com/events/month/2026-04.json")

    assert isinstance(result, GothamPageData), "get_data() did not return GothamPageData"
    assert len(result.event_list) > 0, "get_data() returned 0 events"
    assert result.event_list[0].name == "Gotham Showcase"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: collect_scraping_targets() feeds into get_data()."""
    scraper = GothamComedyClubScraper(_club())
    fake_page_data = GothamPageData(event_list=[_fake_gotham_event()])

    monkeypatch.setattr(
        scraper.extractor,
        "extract_events",
        AsyncMock(return_value=fake_page_data),
    )

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"

    all_events = []
    for url in urls[:2]:  # Only check first 2 months to keep test fast
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
