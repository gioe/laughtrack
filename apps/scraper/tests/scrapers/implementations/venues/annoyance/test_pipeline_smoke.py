"""
Pipeline smoke test for AnnoyanceTheatreScraper.

Exercises collect_scraping_targets() -> get_data() against fixtures
matching the ThunderTix calendar API response structure.
"""

import pytest

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.scrapers.implementations.venues.annoyance.scraper import AnnoyanceTheatreScraper
from laughtrack.scrapers.implementations.venues.annoyance.data import AnnoyancePageData


CALENDAR_URL = "https://theannoyance.thundertix.com/reports/calendar?week=0&start=1743292800&end=1743897600"


def _club() -> Club:
    _c = Club(id=999, name='The Annoyance Theatre', address='851 W. Belmont Ave', website='https://www.theannoyance.com', popularity=0, zip_code='60657', phone_number='', visible=True, timezone='America/Chicago')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://theannoyance.thundertix.com/reports/calendar', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _performance_dict(
    title="Tuesday Musical Improv",
    start="2026-03-24 20:00:00 -0500",
    event_id=207875,
    performance_id=3231744,
    truncated_url="/events/207875",
    order_products_url="/orders/new?event_id=207875&performance_id=3231744",
    publicly_available=True,
) -> dict:
    return {
        "title": title,
        "start": start,
        "event_id": event_id,
        "performance_id": performance_id,
        "time_with_timezone": "Tue - Mar 24, 2026 - 8:00pm CDT",
        "truncated_url": truncated_url,
        "order_products_url": order_products_url,
        "order_tickets_url": None,
        "publicly_available": publicly_available,
        "is_sold_out": False,
    }


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_12_weekly_urls():
    """collect_scraping_targets() must return 12 weekly ThunderTix API URLs."""
    scraper = AnnoyanceTheatreScraper(_club())
    urls = await scraper.collect_scraping_targets()
    assert len(urls) == 12, f"Expected 12 URLs, got {len(urls)}"
    for url in urls:
        assert "thundertix.com/reports/calendar" in url, (
            f"URL does not point to ThunderTix calendar API: {url}"
        )


@pytest.mark.asyncio
async def test_get_data_returns_events_from_api_fixture(monkeypatch):
    """get_data() parses the API JSON array and returns AnnoyancePageData with events."""
    scraper = AnnoyanceTheatreScraper(_club())

    api_fixture = [
        _performance_dict(event_id=1, performance_id=101, title="Tuesday Musical Improv"),
        _performance_dict(event_id=2, performance_id=102, title="Wednesday Night Comedy"),
    ]

    async def fake_fetch_json(self, url: str):
        return api_fixture

    monkeypatch.setattr(AnnoyanceTheatreScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, AnnoyancePageData), "get_data() did not return AnnoyancePageData"
    assert len(result.event_list) == 2, (
        f"Expected 2 events, got {len(result.event_list)}"
    )
    titles = {e.title for e in result.event_list}
    assert "Tuesday Musical Improv" in titles
    assert "Wednesday Night Comedy" in titles


@pytest.mark.asyncio
async def test_get_data_filters_class_events(monkeypatch):
    """get_data() must filter out events whose title starts with 'CLASS:' or 'TRAINING CENTER:'."""
    scraper = AnnoyanceTheatreScraper(_club())

    api_fixture = [
        _performance_dict(event_id=1, performance_id=101, title="Tuesday Musical Improv"),
        _performance_dict(event_id=2, performance_id=102, title="CLASS: Intro to Improv"),
        _performance_dict(event_id=3, performance_id=103, title="TRAINING CENTER: Advanced Scene Work"),
    ]

    async def fake_fetch_json(self, url: str):
        return api_fixture

    monkeypatch.setattr(AnnoyanceTheatreScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, AnnoyancePageData), "get_data() did not return AnnoyancePageData"
    assert len(result.event_list) == 1, (
        f"Expected 1 event after filtering CLASS/TRAINING CENTER, got {len(result.event_list)}"
    )
    assert result.event_list[0].title == "Tuesday Musical Improv"


@pytest.mark.asyncio
async def test_get_data_filters_non_public_events(monkeypatch):
    """get_data() must filter out events where publicly_available is False."""
    scraper = AnnoyanceTheatreScraper(_club())

    api_fixture = [
        _performance_dict(event_id=1, performance_id=101, title="Public Show", publicly_available=True),
        _performance_dict(event_id=2, performance_id=102, title="Private Event", publicly_available=False),
    ]

    async def fake_fetch_json(self, url: str):
        return api_fixture

    monkeypatch.setattr(AnnoyanceTheatreScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(CALENDAR_URL)

    assert isinstance(result, AnnoyancePageData), "get_data() did not return AnnoyancePageData"
    assert len(result.event_list) == 1, (
        f"Expected 1 event after filtering non-public, got {len(result.event_list)}"
    )
    assert result.event_list[0].title == "Public Show"


@pytest.mark.asyncio
async def test_get_data_returns_none_on_empty_response(monkeypatch):
    """get_data() returns None when the API returns an empty array."""
    scraper = AnnoyanceTheatreScraper(_club())

    async def fake_fetch_json(self, url: str):
        return []

    monkeypatch.setattr(AnnoyanceTheatreScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None


@pytest.mark.asyncio
async def test_get_data_returns_none_when_fetch_fails(monkeypatch):
    """get_data() returns None when fetch_json raises an exception."""
    scraper = AnnoyanceTheatreScraper(_club())

    async def fake_fetch_json(self, url: str):
        raise Exception("Connection refused")

    monkeypatch.setattr(AnnoyanceTheatreScraper, "fetch_json", fake_fetch_json)

    result = await scraper.get_data(CALENDAR_URL)
    assert result is None


def test_can_transform_not_defined_on_scraper():
    """AnnoyanceTheatreScraper must not define can_transform() — it's dead code."""
    assert not hasattr(AnnoyanceTheatreScraper, "can_transform") or (
        "can_transform" not in AnnoyanceTheatreScraper.__dict__
    ), "can_transform() must be removed from AnnoyanceTheatreScraper (dead code)"
