"""
Pipeline smoke test for Gotham Comedy Club scraper.

Exercises collect_scraping_targets() (feed pagination, with the network
probe mocked) → get_data() by mocking GothamEventExtractor.extract_events
to return a fixture GothamPageData.
"""

import importlib.util
from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.clients.gotham.models.models import GothamFeedEvent
from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.gotham.scraper import (
    MAX_PAGES,
    PAGE_SIZE,
    GothamComedyClubScraper,
)
from laughtrack.scrapers.implementations.venues.gotham.data import GothamPageData


def _club() -> Club:
    _c = Club(id=99, name='Gotham Comedy Club', address='', website='https://www.gothamcomedyclub.com', popularity=0, zip_code='', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://www.gothamcomedyclub.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _fake_gotham_event() -> GothamFeedEvent:
    return GothamFeedEvent(
        id="6a286dd29da8c9c14b299e74",
        name="Gotham Showcase",
        start="2099-04-15T20:00:00-04:00",
        event_id="10378853",
        slug="gotham-showcase",
    )


def _probe_response(total: int) -> dict:
    return {"items": [], "pagination": {"limit": 1, "offset": 0, "total": total}}


@pytest.mark.asyncio
async def test_collect_scraping_targets_paginates_feed(monkeypatch):
    """collect_scraping_targets() turns pagination.total into feed page URLs."""
    scraper = GothamComedyClubScraper(_club())
    monkeypatch.setattr(scraper, "fetch_json", AsyncMock(return_value=_probe_response(193)))

    urls = await scraper.collect_scraping_targets()

    assert len(urls) == 2, f"193 items at PAGE_SIZE={PAGE_SIZE} should yield 2 pages, got: {urls}"
    assert all("square-mountain-7159.alex-cdc.workers.dev/items" in u for u in urls), (
        f"Expected worker feed URLs, got: {urls}"
    )
    assert f"limit={PAGE_SIZE}&offset=0" in urls[0]
    assert f"limit={PAGE_SIZE}&offset={PAGE_SIZE}" in urls[1]


@pytest.mark.asyncio
async def test_collect_scraping_targets_caps_pages_defensively(monkeypatch):
    """A garbage pagination.total must not generate unbounded targets."""
    scraper = GothamComedyClubScraper(_club())
    monkeypatch.setattr(scraper, "fetch_json", AsyncMock(return_value=_probe_response(10_000_000)))

    urls = await scraper.collect_scraping_targets()

    assert len(urls) == MAX_PAGES


@pytest.mark.asyncio
async def test_collect_scraping_targets_defaults_to_one_page_on_probe_failure(monkeypatch):
    """A failed probe degrades to a single first-page target, not zero."""
    scraper = GothamComedyClubScraper(_club())
    monkeypatch.setattr(scraper, "fetch_json", AsyncMock(side_effect=Exception("boom")))

    urls = await scraper.collect_scraping_targets()

    assert len(urls) == 1
    assert "offset=0" in urls[0]


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

    result = await scraper.get_data(
        "https://square-mountain-7159.alex-cdc.workers.dev/items?limit=100&offset=0"
    )

    assert isinstance(result, GothamPageData), "get_data() did not return GothamPageData"
    assert len(result.event_list) > 0, "get_data() returned 0 events"
    assert result.event_list[0].name == "Gotham Showcase"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: collect_scraping_targets() feeds into get_data()."""
    scraper = GothamComedyClubScraper(_club())
    fake_page_data = GothamPageData(event_list=[_fake_gotham_event()])

    monkeypatch.setattr(scraper, "fetch_json", AsyncMock(return_value=_probe_response(193)))
    monkeypatch.setattr(
        scraper.extractor,
        "extract_events",
        AsyncMock(return_value=fake_page_data),
    )

    urls = await scraper.collect_scraping_targets()
    assert len(urls) > 0, "collect_scraping_targets() returned 0 URLs"

    all_events = []
    for url in urls[:2]:  # Only check first 2 pages to keep test fast
        page_data = await scraper.get_data(url)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
