"""
Pipeline smoke test for Comedy Cellar scraper.

Exercises collect_scraping_targets() → get_data() by replacing the API client
with a lightweight fake and patching the extractor for fixture events.
"""

import importlib.util
from typing import List, Optional

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("curl_cffi") is None,
    reason="curl_cffi not installed",
)

from laughtrack.core.entities.club.model import Club, ScrapingSource
from laughtrack.core.entities.event.comedy_cellar import ComedyCellarEvent
from laughtrack.foundation.models.api.comedy_cellar.models import (
    ComedyCellarLineupAPIResponse,
    ComedyCellarShowsAPIResponse,
    DateAbbreviation,
    ShowAge,
    ShowInfoData,
    ShowsDataContainer,
    ShowsInfoData,
)
from laughtrack.scrapers.implementations.venues.comedy_cellar import extractor as extractor_mod
from laughtrack.scrapers.implementations.venues.comedy_cellar.data import ComedyCellarDateData
from laughtrack.scrapers.implementations.venues.comedy_cellar.scraper import ComedyCellarScraper


API_DATE = "2026-04-15"


def _club() -> Club:
    _c = Club(id=99, name='Comedy Cellar', address='', website='https://www.comedycellar.com', popularity=0, zip_code='', phone_number='', visible=True, timezone='America/New_York')
    _c.active_scraping_source = ScrapingSource(id=1, club_id=_c.id, platform='custom', scraper_key='', source_url='https://www.comedycellar.com', external_id=None)
    _c.scraping_sources = [_c.active_scraping_source]
    return _c


def _make_lineup(api_date: str = API_DATE) -> ComedyCellarLineupAPIResponse:
    payload = {
        "show": {"html": "<div>Comedian A</div>", "date": "Wednesday April 15, 2026"},
        "date": api_date,
        "dates": {api_date: "Wednesday April 15, 2026"},
    }
    return ComedyCellarLineupAPIResponse.from_dict(payload)


def _make_shows(api_date: str = API_DATE) -> ComedyCellarShowsAPIResponse:
    show_info = ShowInfoData(
        id=1001,
        time="20:00:00",
        description="Main Show",
        roomId=1,
        timestamp=1776000000,
    )
    info = ShowsInfoData(
        date=api_date,
        prettyDate="Wed Apr 15, 2026",
        abbr=DateAbbreviation(day="Wed", month="Apr", date="15", pretty="Apr 15"),
        shows=[show_info],
        age=ShowAge(seconds=0, time=0),
    )
    return ComedyCellarShowsAPIResponse(message="Ok", data=ShowsDataContainer(showInfo=info))


def _fake_cellar_event(api_date: str = API_DATE) -> ComedyCellarEvent:
    return ComedyCellarEvent(
        show_id=1001,
        date_key=api_date,
        api_time="20:00:00",
        show_name="Comedy Cellar Showcase",
        description="A great night of comedy",
        note=None,
        room_id=1,
        room_name="Village Underground",
        timestamp=1776000000,
        ticket_link=f"https://www.comedycellar.com/reservations-newyork/?showid=1001",
        ticket_data=ShowInfoData(id=1001, time="20:00:00", description="Main Show", roomId=1, timestamp=1776000000),
        html_container="<div>Comedian A</div>",
        lineup_names=["Comedian A"],
    )


class _FakeAPIClient:
    """Minimal fake ComedyCellarAPIClient for pipeline smoke tests."""

    async def discover_available_dates(self) -> List[str]:
        return [API_DATE]

    async def get_lineup_data(self, target: str) -> ComedyCellarLineupAPIResponse:
        return _make_lineup(target)

    async def get_shows_data(self, target: str) -> ComedyCellarShowsAPIResponse:
        return _make_shows(target)


@pytest.mark.asyncio
async def test_collect_scraping_targets_returns_dates():
    """collect_scraping_targets() returns date strings from the API client."""
    scraper = ComedyCellarScraper(_club())
    scraper.api_client = _FakeAPIClient()

    dates = await scraper.collect_scraping_targets()
    assert len(dates) > 0, "collect_scraping_targets() returned 0 dates"
    assert dates[0] == API_DATE


@pytest.mark.asyncio
async def test_get_data_returns_events_from_api_fixtures(monkeypatch):
    """get_data() combines lineup + shows API responses into ComedyCellarDateData."""
    scraper = ComedyCellarScraper(_club())
    scraper.api_client = _FakeAPIClient()

    def fake_extract(date_key, lineup, shows):
        return [_fake_cellar_event(date_key)]

    monkeypatch.setattr(
        extractor_mod.ComedyCellarExtractor, "extract_events", staticmethod(fake_extract)
    )

    result = await scraper.get_data(API_DATE)

    assert isinstance(result, ComedyCellarDateData), "get_data() did not return ComedyCellarDateData"
    assert len(result.event_list) > 0, "get_data() returned 0 events"
    assert result.event_list[0].show_name == "Comedy Cellar Showcase"


@pytest.mark.asyncio
async def test_full_pipeline_discover_then_get_data(monkeypatch):
    """Full pipeline: collect_scraping_targets() feeds into get_data()."""
    scraper = ComedyCellarScraper(_club())
    scraper.api_client = _FakeAPIClient()

    def fake_extract(date_key, lineup, shows):
        return [_fake_cellar_event(date_key)]

    monkeypatch.setattr(
        extractor_mod.ComedyCellarExtractor, "extract_events", staticmethod(fake_extract)
    )

    dates = await scraper.collect_scraping_targets()
    assert len(dates) > 0, "collect_scraping_targets() returned 0 dates"

    all_events = []
    for date in dates:
        page_data = await scraper.get_data(date)
        if page_data:
            all_events.extend(page_data.event_list)

    assert len(all_events) > 0, "Full pipeline produced 0 events"
